"""
改进的多模态 RAG 智能体 (v3-improved)
使用选择性提取策略,仅提取和存储PDF中的图片和公式
"""
import os
import sys
from typing import List, Tuple, Dict
from pathlib import Path

from langchain_core.documents import Document

# 导入v3本地组件
from qwen_embedding import QwenEmbedding

# 导入v3组件
from config_v3 import ConfigV3
from vector_store_v3 import VectorStoreV3
from gemini_chat_model import GeminiChatModel
from figure_extractor import FigureExtractor
# 使用改进的公式提取器(支持OCR)
try:
    from formula_extractor_ocr import FormulaExtractorOCR as FormulaExtractor
    print("[RAG] 使用FormulaExtractorOCR (支持LaTeX)")
except ImportError:
    from formula_extractor import FormulaExtractor
    print("[RAG] 使用基础FormulaExtractor")
from multimodal_index import MultimodalIndex
from content_linker import ContentLinker

# 导入重排序器(可选)
try:
    from reranker import ReRanker
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    print("[RAG] 重排序器不可用,将跳过重排序步骤")


class RAGAgentV3Improved:
    """改进的多模态RAG智能体"""
    
    def __init__(self, config_path: str = ".env"):
        """
        初始化RAG智能体
        
        Args:
            config_path: 配置文件路径
        """
        print("=" * 60)
        print("初始化 RAG v3-improved 多模态智能体...")
        print("=" * 60)
        
        # 1. 加载配置
        print("\n[1/6] 加载配置...")
        self.config = ConfigV3(config_path)
        print("✓ 配置加载成功")
        
        # 2. 初始化Embedding模型(复用v2的Qwen Embedding)
        print("\n[2/6] 初始化Embedding模型...")
        self.embedding_model = QwenEmbedding(self.config._base)
        print("✓ Embedding模型初始化成功(Qwen)")
        
        # 3. 初始化向量库
        print("\n[3/6] 初始化向量数据库...")
        self.vector_store = VectorStoreV3(self.config, self.embedding_model)
        if not self.vector_store.build_vectorstore(force_rebuild=False):
            print("⚠ 向量库不存在或加载失败, 请执行 rebuild_knowledge_base()")
        
        # 4. 初始化Gemini多模态模型
        print("\n[4/6] 初始化Gemini聊天模型...")
        self.chat_model = GeminiChatModel(self.config)
        print("✓ Gemini模型初始化成功")
        
        # 5. 初始化多模态索引
        print("\n[5/6] 初始化多模态索引...")
        self.multimodal_index = MultimodalIndex()
        
        # 6. 初始化提取器
        print("\n[6/6] 初始化提取器...")
        self.figure_extractor = FigureExtractor()
        self.formula_extractor = FormulaExtractor()
        print("✓ 提取器初始化成功")
        
        # 7. 初始化重排序器(可选)
        self.reranker = None
        if RERANKER_AVAILABLE:
            try:
                self.reranker = ReRanker()
                print("✓ 重排序器初始化成功")
            except Exception as e:
                print(f"⚠ 重排序器初始化失败: {e}")
        
        print("\n" + "=" * 60)
        print("RAG v3-improved 初始化完成!")
        print("=" * 60 + "\n")
    

    def rebuild_knowledge_base(self, target_filename: str = None) -> bool:
        """
        重建知识库 (支持增量更新)
        
        Args:
            target_filename: 指定要重建的文件名(如 "LDO.pdf")。如果为None，则重建所有。
        """
        print("\n" + "=" * 60)
        mode_str = f"增量更新: {target_filename}" if target_filename else "全量重建"
        print(f"开始 {mode_str} 知识库...")
        print("=" * 60)
        
        # 0. 准备文件列表
        all_pdf_files = self._get_pdf_files()
        if not all_pdf_files:
            print("⚠ 未找到PDF文件")
            return False
            
        target_files = []
        if target_filename:
            # 查找匹配的文件
            for f in all_pdf_files:
                if os.path.basename(f) == target_filename:
                    target_files.append(f)
                    break
            if not target_files:
                print(f"✗ 未找到指定文件: {target_filename}")
                return False
        else:
            target_files = all_pdf_files
            # 全量重建时才清空索引
            self.multimodal_index.clear()
        
        # 1. 提取图片和公式
        print(f"\n[步骤 1/4] 提取图片和公式 (文件数: {len(target_files)})...")
        current_figures = []
        current_formulas = []
        
        for pdf_file in target_files:
            print(f"\n处理: {os.path.basename(pdf_file)}")
            
            # 提取
            figures = self.figure_extractor.extract_figures(pdf_file)
            current_figures.extend(figures)
            
            formulas = self.formula_extractor.extract_formulas(pdf_file)
            current_formulas.extend(formulas)
            
            # 更新多模态索引
            # 如果是增量更新，最好先删除旧的条目？MultimodalIndex目前不支持删，但直接覆盖ID即可
            for fig in figures:
                self.multimodal_index.add_figure(fig)
            for eq in formulas:
                self.multimodal_index.add_formula(eq)
        
        print(f"\n✓ 提取完成:")
        print(f"  - 图片: {len(current_figures)} 个")
        print(f"  - 公式: {len(current_formulas)} 个")
        
        # 2. 更新向量库
        print("\n[步骤 2/4] 更新文本向量库...")
        
        if target_filename:
            # 增量模式: 先删后加
            target_path = target_files[0]
            # 1. 删除旧文档
            self.vector_store.delete_document_by_source(os.path.basename(target_path))
            # 2. 添加新文档
            ok = self.vector_store.add_document(target_path)
            if not ok:
                print("✗ 增量更新向量库失败")
                return False
        else:
            # 全量模式
            ok = self.vector_store.build_vectorstore(force_rebuild=True)
            if not ok:
                print("✗ 全量构建向量库失败")
                return False
        
        # 3. 关联文本与图片/公式
        print("\n[步骤 3/4] 关联文本与图片/公式...")
        # 注意: 这里最好只重链当前文件的，但为了简单可靠，可以全量重链(性能损耗不大)
        # 或者只获取新加文档的 chunks。
        # 简单起见，重新加载所有 chunks 进行链接 (ContentLinker 比较快)
        text_docs = self._get_all_text_chunks()
        
        if not text_docs:
            print("⚠ 未找到文本块,跳过关联")
        else:
            # 需要所有图片公式来做全量链接吗？
            # 是的，因为MultimodalIndex已经包含了所有(全量或增量add之后)
            # 但我们需要把MultimodalIndex里已有的所有items拿出来传给linker
            # Index类里没有直接导出所有items的方法，我们需要加一个或者...
            # 其实ContentLinker只需要Index本身就可以工作，看它的实现。
            # 检查 content_linker.py ... 假设它需要 index。
            # rag_agent_v3_improved.py L162: linker = ContentLinker(self.multimodal_index)
            # linker.link_documents 需要 figures, formulas list.
            
            # 小Hack: 从 index 内部 storage 获取所有 items
            all_figs = list(self.multimodal_index.index['figures'].values())
            all_eqs = list(self.multimodal_index.index['formulas'].values())
            
            linker = ContentLinker(self.multimodal_index)
            linker.link_documents(text_docs, all_figs, all_eqs)
        
        # 4. 保存索引
        print("\n[步骤 4/4] 保存索引...")
        self.multimodal_index.save()
        
        # 打印统计
        print("\n" + "=" * 60)
        self.multimodal_index.print_statistics()
        print("=" * 60)
        print("✓ 知识库更新完成!\n")
        
        return True
    
    def sync_knowledge_base(self, force: bool = False):
        """
        同步知识库 (自动发现新文件并添加)
        
        Args:
            force: 是否强制重新处理所有文件
        """
        print("\n" + "=" * 60)
        mode = "强制同步 (重新处理所有文件)" if force else "增量同步 (仅处理新文件)"
        print(f"开始 {mode}...")
        print("=" * 60)
        
        # 1. 获取所有PDF文件
        all_pdf_files = self._get_pdf_files()
        if not all_pdf_files:
            print("⚠ 未找到PDF文件")
            return
            
        print(f"扫描到 {len(all_pdf_files)} 个PDF文件")
        
        target_files = []
        
        if force:
            # 强制模式: 所有文件都是目标
            target_files = all_pdf_files
            print(f"强制模式: 将重新处理所有 {len(target_files)} 个文件")
        else:
            # 增量模式: 找出新文件
            # 2. 获取已索引的文件
            existing_sources = self.vector_store.get_existing_sources()
            print(f"数据库中已有 {len(existing_sources)} 个文件")
            
            # 3. 找出新文件
            for f in all_pdf_files:
                if os.path.basename(f) not in existing_sources:
                    target_files.append(f)
            
            if not target_files:
                print("✓ 知识库已是最新，无需同步")
                return
                
            print(f"\n发现 {len(target_files)} 个新文件，准备处理:")
            for f in target_files:
                print(f"  - {os.path.basename(f)}")
            
        # 4. 逐个处理
        success_count = 0
        for i, f in enumerate(target_files, 1):
            filename = os.path.basename(f)
            print(f"\n>>> 处理进度 [{i}/{len(target_files)}]: {filename}")
            if self.rebuild_knowledge_base(target_filename=filename):
                success_count += 1
            else:
                print(f"✗ 文件 {filename} 处理失败")
                
        print("\n" + "=" * 60)
        print(f"同步完成! 成功: {success_count}/{len(target_files)}")
        print("=" * 60 + "\n")
    
    def retrieve_context(
        self,
        query: str,
        k: int = 10,  # 增加到10以获得更好的覆盖
        max_images: int = 6,
        source_filter: str = None
    ) -> Tuple[str, List[str], List[str]]:
        """
        检索上下文
        
        Args:
            query: 查询文本
            k: 检索文本块数量
            max_images: 最大图片数量(包括图片和公式)
            source_filter: 可选, 按文档名筛选
            
        Returns:
            (文本上下文, 图片路径列表, 公式图片路径列表)
        """
        if not self.vector_store.vectorstore:
            return "", [], []
        
        # 1. 使用MMR检索,减少冗余
        docs = self.vector_store.search(
            query, 
            k=k, 
            use_mmr=True,
            fetch_k=k * 3,  # 先获取30个候选,再用MMR筛选出10个
            source_filter=source_filter
        )
        
        if not docs:
            return "", [], []
        
        # 2. 邻近页面扩展,确保上下文完整
        docs = self.vector_store.expand_neighbors_by_page(
            docs,
            page_window=1,
            max_total=12  # 最终保留12个文档块
        )
        
        # 3. 重排序(可选)
        if self.reranker and len(docs) > k:
            docs = self.reranker.rerank(query, docs, top_k=k)
        
        # 4. 获取关联的图片和公式 (增强版：多策略)
        all_figures = []
        all_formulas = []
        
        # 策略 1: 检测 query 中的 Figure/Formula 关键词，直接搜索
        import re
        fig_match = re.search(r'(Figure|Fig\.?)\s*(\d+)', query, re.IGNORECASE)
        if fig_match:
            fig_keyword = f"{fig_match.group(1)} {fig_match.group(2)}"
            print(f"[v3] 检测到图片查询: '{fig_keyword}'，使用 Caption 搜索")
            caption_figs = self.multimodal_index.search_figures_by_caption(fig_keyword, source_filter)
            all_figures.extend(caption_figs)
        
        formula_match = re.search(r'(\d+\.\d+|\(\d+\)|\[\d+\])', query)
        if formula_match:
            formula_num = formula_match.group(1).strip('()[]')
            print(f"[v3] 检测到公式查询: '{formula_num}'，使用编号搜索")
            caption_formulas = self.multimodal_index.search_formulas_by_id(formula_num, source_filter)
            all_formulas.extend(caption_formulas)
        
        # 策略 2: 基于检索到的文本块，按 Page 查找图片和公式
        for doc in docs:
            meta = doc.metadata or {}
            source = meta.get('source', '')
            page = meta.get('page', -1)
            
            if source and page >= 0:
                # 获取同一页的图片
                page_figs = self.multimodal_index.get_figures_by_page(os.path.basename(source), page)
                all_figures.extend(page_figs)
            
            # 保留原有的 chunk_id 关联逻辑作为备选
            figures = self.multimodal_index.get_related_figures(doc)
            formulas = self.multimodal_index.get_related_formulas(doc)
            all_figures.extend(figures)
            all_formulas.extend(formulas)
        
        # 5. 去重
        unique_figures = self._deduplicate_by_id(all_figures, 'figure_id')
        unique_formulas = self._deduplicate_by_id(all_formulas, 'formula_id')
        
        print(f"[v3] 多模态检索完成: {len(unique_figures)} 个图片, {len(unique_formulas)} 个公式")
        
        # 6. 限制数量(优先公式,因为通常更重要)
        formula_paths = [f['image_path'] for f in unique_formulas[:max_images]]
        remaining = max_images - len(formula_paths)
        figure_paths = [f['image_path'] for f in unique_figures[:remaining]]
        
        # 7. 组装文本上下文
        context_parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata or {}
            source = meta.get('source', '未知')
            page = meta.get('page', '?')
            source_name = os.path.basename(source) if source != '未知' else source
            context_parts.append(
                f"[文档{i}] 来源: {source_name}, 页码: {page}\n{doc.page_content}\n"
            )
        
        # 8. 添加图片和公式信息
        if unique_figures:
            context_parts.append("\n【相关图片】:")
            for fig in unique_figures[:remaining]:
                caption = fig.get('caption', fig['figure_id'])
                context_parts.append(f"- {caption} (页码: {fig['page']})")
        
        if unique_formulas:
            context_parts.append("\n【相关公式】:")
            for eq in unique_formulas[:max_images]:
                context_text = eq.get('context', '')
                text = eq.get('text', '')
                latex = eq.get('latex', '')  # 新增LaTeX
                
                # 优先显示LaTeX,其次是原始文本
                if latex:
                    context_parts.append(f"- {context_text} (页码: {eq['page']})")
                    context_parts.append(f"  LaTeX: {latex}")
                elif context_text:
                    context_parts.append(f"- {context_text} {text} (页码: {eq['page']})")
                else:
                    context_parts.append(f"- {text} (页码: {eq['page']})")
        
        context_text = "\n".join(context_parts)
        
        return context_text, figure_paths, formula_paths
    
    def chat(
        self, 
        message: str, 
        use_rag: bool = True, 
        k: int = 5,
        max_images: int = 6
    ) -> str:
        """
        多模态对话接口
        
        Args:
            message: 用户消息
            use_rag: 是否使用RAG
            k: 检索文本块数量
            max_images: 最大图片数量
            
        Returns:
            AI回复
        """
        if not use_rag or not self.vector_store.vectorstore:
            return self.chat_model.chat(message)
        
        # 检索上下文
        context, fig_paths, eq_paths = self.retrieve_context(message, k=k, max_images=max_images)
        
        # 判断检索质量
        if not context or len(context) < 100:
            print("[RAG] 检索内容不足,使用混合模式")
            # 使用混合Prompt,允许LLM自由发挥
            hybrid_prompt = f"""请作为模拟电路设计专家回答以下问题:

{message}

提示: 知识库中相关内容有限,请结合你的专业知识给出完整、详细的回答。
"""
            return self.chat_model.chat(hybrid_prompt)
        
        # 合并图片和公式路径
        all_images = eq_paths + fig_paths  # 公式优先
        
        # 构建优化的Prompt - 允许LLM结合自身知识
        prompt = f"""你是模拟电路设计领域的资深专家。

【知识库检索结果】:
{context}

【用户问题】:
{message}

【回答指南】:
1. **优先参考**检索到的知识库内容,这些是专业教材的权威信息
2. **结合你的专业知识**对检索内容进行补充、解释和扩展
3. 如果检索内容不完整,请基于你的领域知识进行合理推断,但需明确标注
4. 对于公式:
   - 解释各变量的物理含义和取值范围
   - 说明公式的适用条件和应用场景
   - 如有相关推导,请简要说明
5. 对于电路图:
   - 分析拓扑结构和关键元件
   - 解释工作原理和信号流向
   - 指出设计要点和常见问题
6. 信息来源标注:
   - 来自知识库: "根据文档X"、"教材第X页提到"
   - 来自推断: "根据电路原理"、"通常情况下"、"从设计经验来看"

【回答要求】:
- 给出**完整、专业、深入**的技术回答
- 即使检索内容有限,也要尽可能提供有价值的分析和见解
- 保持技术准确性、逻辑连贯性和实用性
- 回答要有层次,先概述再详述

请详细回答:
"""
        
        # 调用多模态LLM
        if all_images:
            # 过滤不存在的图片
            valid_images = [img for img in all_images if os.path.exists(img)]
            if valid_images:
                return self.chat_model.chat_with_images(prompt, valid_images)
        
        # 没有图片或图片不存在,使用纯文本
        return self.chat_model.chat(prompt)
    
    def search_knowledge_base(
        self, 
        query: str, 
        k: int = 5
    ) -> Tuple[List[Document], List[Dict], List[Dict]]:
        """
        搜索知识库
        
        Args:
            query: 查询文本
            k: 返回结果数量
            
        Returns:
            (文本块列表, 图片列表, 公式列表)
        """
        if not self.vector_store.vectorstore:
            return [], [], []
        
        # 检索文本
        docs = self.vector_store.search(query, k=k)
        
        # 获取关联的图片和公式
        figures = []
        formulas = []
        for doc in docs:
            figures.extend(self.multimodal_index.get_related_figures(doc))
            formulas.extend(self.multimodal_index.get_related_formulas(doc))
        
        # 去重
        unique_figures = self._deduplicate_by_id(figures, 'figure_id')
        unique_formulas = self._deduplicate_by_id(formulas, 'formula_id')
        
        return docs, unique_figures, unique_formulas
    
    def _deduplicate_by_id(self, items: List[Dict], id_key: str) -> List[Dict]:
        """按ID去重"""
        seen = set()
        unique = []
        for item in items:
            item_id = item.get(id_key)
            if item_id and item_id not in seen:
                seen.add(item_id)
                unique.append(item)
        return unique
    
    def _get_pdf_files(self) -> List[str]:
        """获取所有PDF文件路径"""
        pdf_files = []
        docs_dir = self.config.documents_dir
        
        if not os.path.exists(docs_dir):
            print(f"⚠ 文档目录不存在: {docs_dir}")
            return []
        
        for root, _, files in os.walk(docs_dir):
            for f in files:
                if f.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, f))
        
        return pdf_files
    
    def _get_all_text_chunks(self) -> List[Document]:
        """获取向量库中的所有文本块"""
        if not self.vector_store.vectorstore:
            return []
        
        try:
            data = self.vector_store.vectorstore.get(include=["documents", "metadatas"])
            documents = data.get("documents", [])
            metadatas = data.get("metadatas", [])
            
            return [
                Document(page_content=doc, metadata=meta)
                for doc, meta in zip(documents, metadatas)
            ]
        except Exception as e:
            print(f"[RAGAgentV3Improved] 获取文本块失败: {e}")
            return []


if __name__ == "__main__":
    # 测试代码
    print("RAG v3-improved 测试")
    print("=" * 60)
    
    try:
        agent = RAGAgentV3Improved()
        print("\n✓ 智能体初始化成功")
        
        # 提示用户
        print("\n可用命令:")
        print("  - agent.rebuild_knowledge_base()  # 重建知识库")
        print("  - agent.chat('你的问题')          # 对话")
        print("  - agent.search_knowledge_base('查询')  # 搜索")
        
    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()

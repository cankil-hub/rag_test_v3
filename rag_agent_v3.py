"""
v3 多模态 RAG 智能体
使用:
 - Qwen Embedding + Chroma 做文本检索
 - PDF 页图作为图像上下文
 - Gemini 2.x (flash) 作为多模态回答模型
"""
import os
from typing import List, Tuple

from langchain_core.documents import Document

from qwen_embedding import QwenEmbedding
from .config_v3 import ConfigV3
from .vector_store_v3 import VectorStoreV3
from .pdf_page_images import export_pdf_pages_to_images
from .gemini_chat_model import GeminiChatModel


class RAGAgentV3:
    """多模态 RAG 主类"""

    def __init__(self, config_path: str = ".env"):
        print("=" * 60)
        print("初始化 RAG v3 多模态智能体...")
        print("=" * 60)

        # 1. 配置
        self.config = ConfigV3(config_path)
        print("[v3] 配置加载成功")

        # 2. Embedding (沿用 QwenEmbedding)
        self.embedding_model = QwenEmbedding(self.config._base)  # 直接使用基础 Config
        print("[v3] Embedding 模型初始化成功(Qwen)")

        # 3. 向量库
        self.vector_store = VectorStoreV3(self.config, self.embedding_model)
        if not self.vector_store.build_vectorstore(force_rebuild=False):
            print("[v3] 向量库不存在或加载失败, 请先执行重建")

        # 4. Gemini 多模态模型
        self.chat_model = GeminiChatModel(self.config)
        print("[v3] Gemini 聊天模型初始化成功")

        # 5. PDF 页图准备（懒加载，由用户触发重建时执行）
        print("[v3] 初始化完成, 可使用 /rebuild_v3 构建知识库+页图")
        print("=" * 60)

    # ========== 知识库相关 ==========
    def rebuild_knowledge_base(self) -> bool:
        """重建 v3 知识库+PDF 页图"""
        print("\n[v3] 开始重建 v3 知识库...")
        ok = self.vector_store.build_vectorstore(force_rebuild=True)
        if not ok:
            return False

        # 导出 PDF 页图
        export_pdf_pages_to_images(
            self.config.documents_dir,
            self.config.page_image_dir,
        )
        return True

    def _image_path_for_doc(self, doc: Document) -> str:
        """根据文档 metadata 推导所在页的图片路径"""
        meta = doc.metadata or {}
        source = meta.get("source") or meta.get("file_path") or meta.get("path")
        page = meta.get("page")
        if not source or page is None:
            return ""

        base = os.path.splitext(os.path.basename(str(source)))[0]
        try:
            page_idx = int(page)
        except Exception:
            return ""

        img_name = f"{base}_page_{page_idx}.png"
        img_path = os.path.join(self.config.page_image_dir, img_name)
        return img_path

    def retrieve_context(
        self,
        query: str,
        k: int = 5,
        max_images: int = 4,
    ) -> Tuple[str, List[str]]:
        """
        检索文本上下文, 并找出对应的 PDF 页图路径

        Returns:
            (上下文字符串, 图片路径列表)
        """
        if not self.vector_store.vectorstore:
            return "", []

        docs = self.vector_store.search(query, k=k)
        if not docs:
            return "", []

        # 组装上下文文字
        ctx_parts: List[str] = []
        image_paths: List[str] = []
        added_images = set()

        for i, d in enumerate(docs, 1):
            meta = d.metadata or {}
            source = meta.get("source") or meta.get("file_path") or meta.get("path") or "未知来源"
            page = meta.get("page")
            page_info = f"(页码: {page})" if page is not None else ""
            ctx_parts.append(f"[文档{i}] 来源: {source} {page_info}\n{d.page_content}\n")

            if len(image_paths) < max_images:
                img_path = self._image_path_for_doc(d)
                if img_path and os.path.exists(img_path) and img_path not in added_images:
                    image_paths.append(img_path)
                    added_images.add(img_path)

        context_text = "\n".join(ctx_parts)
        return context_text, image_paths

    # ========== 对话接口 ==========
    def chat(self, message: str, use_rag: bool = True, k: int = 5) -> str:
        """
        多模态对话接口:
        - use_rag=True 时, 使用检索到的文本+页图作为上下文调用 Gemini
        - use_rag=False 时, 直接调用 Gemini
        """
        if not use_rag or not self.vector_store.vectorstore:
            return self.chat_model.chat(message)

        context, image_paths = self.retrieve_context(message, k=k)

        if not context and not image_paths:
            # 没有命中, 回退到纯模型回答
            return self.chat_model.chat(message)

        prompt = f"""你是一名电源管理与模拟 IC 领域的专家。
下面是从知识库中检索到的文本上下文，以及对应 PDF 页面的截图(如果有)。
请结合文字和图片, 回答用户的问题。

【检索到的上下文】:
{context}

【用户问题】:
{message}

回答要求:
1. 尽量从上下文和图片中提取信息, 优先引用文档中的关键结论和公式;
2. 若需要使用一般电源管理理论进行补充, 请标注“[推导]”;
3. 结构化输出, 尤其是等效模型、公式推导、参数含义等部分。
"""
        if image_paths:
            return self.chat_model.chat_with_images(prompt, image_paths)
        else:
            return self.chat_model.chat(prompt)



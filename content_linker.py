"""
内容关联器
自动关联文本块与图片/公式
"""
from typing import List, Dict
from langchain_core.documents import Document
import re


class ContentLinker:
    """内容关联器 - 自动关联文本、图片、公式"""
    
    def __init__(self, multimodal_index):
        """
        初始化内容关联器
        
        Args:
            multimodal_index: MultimodalIndex实例
        """
        self.index = multimodal_index
        print("[ContentLinker] 初始化完成")
    
    def link_documents(
        self, 
        text_docs: List[Document],
        figures: List[Dict],
        formulas: List[Dict]
    ):
        """
        关联文本块与图片/公式
        
        策略:
        1. 基于页码: 同一页的内容关联
        2. 基于引用: 文本中提到"图1.1"则关联对应图片
        3. 基于距离: 公式与前后文本块关联
        
        Args:
            text_docs: 文本块列表
            figures: 图片元数据列表
            formulas: 公式元数据列表
        """
        print(f"[ContentLinker] 开始关联:")
        print(f"  - 文本块: {len(text_docs)}")
        print(f"  - 图片: {len(figures)}")
        print(f"  - 公式: {len(formulas)}")
        
        # 按页码组织内容
        pages = self._organize_by_page(text_docs, figures, formulas)
        
        # 逐页执行关联
        total_links = 0
        for page_num, content in pages.items():
            links = self._link_page_content(
                content['texts'],
                content['figures'],
                content['formulas']
            )
            total_links += links
        
        print(f"[ContentLinker] 关联完成: 共建立 {total_links} 个关联")
    
    def _organize_by_page(
        self,
        text_docs: List[Document],
        figures: List[Dict],
        formulas: List[Dict]
    ) -> Dict[int, Dict]:
        """
        按页码组织内容
        
        Returns:
            {
                page_num: {
                    'texts': [Document],
                    'figures': [Dict],
                    'formulas': [Dict]
                }
            }
        """
        pages = {}
        
        # 组织文本块
        for doc in text_docs:
            page = doc.metadata.get('page', -1)
            if page not in pages:
                pages[page] = {'texts': [], 'figures': [], 'formulas': []}
            pages[page]['texts'].append(doc)
        
        # 组织图片
        for fig in figures:
            page = fig.get('page', -1)
            if page not in pages:
                pages[page] = {'texts': [], 'figures': [], 'formulas': []}
            pages[page]['figures'].append(fig)
        
        # 组织公式
        for eq in formulas:
            page = eq.get('page', -1)
            if page not in pages:
                pages[page] = {'texts': [], 'figures': [], 'formulas': []}
            pages[page]['formulas'].append(eq)
        
        return pages
    
    def _link_page_content(
        self,
        texts: List[Document],
        figures: List[Dict],
        formulas: List[Dict]
    ) -> int:
        """
        关联单页内容
        
        Returns:
            建立的关联数量
        """
        link_count = 0
        
        # 策略1: 基于引用关联图片
        for text_doc in texts:
            content = text_doc.page_content
            chunk_id = self.index._get_chunk_id(text_doc)
            
            # 查找图片引用
            fig_refs = self._extract_figure_references(content)
            
            for fig in figures:
                caption = fig.get('caption', '')
                
                # 匹配策略:
                # 1. 文本中的引用与图注匹配
                if self._match_figure_reference(fig_refs, caption):
                    self.index.link_text_to_figure(chunk_id, fig['figure_id'])
                    link_count += 1
                    continue
                
                # 2. 图注包含在文本中
                if caption and len(caption) > 5 and caption in content:
                    self.index.link_text_to_figure(chunk_id, fig['figure_id'])
                    link_count += 1
                    continue
                
                # 3. 文本块很短且包含"如图所示"等关键词
                if len(content) < 150:
                    if any(kw in content for kw in ['如图', '见图', '如下图', '上图', '下图', 
                                                      'shown in', 'see Fig', 'as shown']):
                        self.index.link_text_to_figure(chunk_id, fig['figure_id'])
                        link_count += 1
        
        # 策略2: 公式与文本关联
        for text_doc in texts:
            content = text_doc.page_content
            chunk_id = self.index._get_chunk_id(text_doc)
            
            for eq in formulas:
                eq_text = eq.get('text', '')
                eq_context = eq.get('context', '')
                
                # 匹配策略:
                # 1. 公式文本出现在文本块中
                if eq_text and len(eq_text) > 5 and eq_text in content:
                    self.index.link_text_to_formula(chunk_id, eq['formula_id'])
                    link_count += 1
                    continue
                
                # 2. 公式上下文与文本块匹配
                if eq_context and len(eq_context) > 10:
                    # 计算相似度(简单的包含关系)
                    if eq_context in content or content in eq_context:
                        self.index.link_text_to_formula(chunk_id, eq['formula_id'])
                        link_count += 1
                        continue
                
                # 3. 文本包含公式关键词
                if any(kw in content for kw in ['公式', '方程', '表达式', 'equation', 'formula']):
                    # 检查是否有数学符号
                    if any(sym in content for sym in ['=', '+', '-', '*', '/']):
                        # 保守策略:仅当文本较短时关联
                        if len(content) < 200:
                            self.index.link_text_to_formula(chunk_id, eq['formula_id'])
                            link_count += 1
        
        return link_count
    
    def _extract_figure_references(self, text: str) -> List[str]:
        """
        提取文本中的图片引用
        
        例如: "图1.1", "Figure 1.1", "Fig. 1-1"
        
        Returns:
            引用列表
        """
        refs = []
        
        # 中文图注: 图1.1, 图 1-1, 图1.1.1
        pattern_cn = r'图\s*[\d\.\-]+'
        refs.extend(re.findall(pattern_cn, text))
        
        # 英文图注: Figure 1.1, Fig. 1-1, Fig 1.1
        pattern_en = r'(?:Figure|Fig\.?)\s*[\d\.\-]+'
        refs.extend(re.findall(pattern_en, text, re.IGNORECASE))
        
        return refs
    
    def _match_figure_reference(self, refs: List[str], caption: str) -> bool:
        """
        判断引用是否与图注匹配
        
        Args:
            refs: 引用列表 (如["图1.1", "Figure 2.3"])
            caption: 图注文本
            
        Returns:
            是否匹配
        """
        if not refs or not caption:
            return False
        
        for ref in refs:
            # 提取引用中的数字部分
            ref_numbers = re.findall(r'[\d\.\-]+', ref)
            
            for num in ref_numbers:
                # 检查图注中是否包含相同的数字
                if num in caption:
                    return True
        
        return False
    
    def link_by_proximity(
        self,
        text_docs: List[Document],
        figures: List[Dict],
        formulas: List[Dict],
        page_window: int = 1
    ):
        """
        基于邻近度关联(跨页)
        
        将相邻页面的图片/公式也关联到文本块
        
        Args:
            text_docs: 文本块列表
            figures: 图片列表
            formulas: 公式列表
            page_window: 页面窗口大小
        """
        print(f"[ContentLinker] 基于邻近度关联 (窗口: ±{page_window}页)")
        
        link_count = 0
        
        for text_doc in text_docs:
            text_page = text_doc.metadata.get('page', -1)
            if text_page == -1:
                continue
            
            chunk_id = self.index._get_chunk_id(text_doc)
            
            # 关联邻近页面的图片
            for fig in figures:
                fig_page = fig.get('page', -1)
                if abs(fig_page - text_page) <= page_window:
                    # 检查是否已关联
                    existing = self.index.index['text_to_figures'].get(chunk_id, [])
                    if fig['figure_id'] not in existing:
                        self.index.link_text_to_figure(chunk_id, fig['figure_id'])
                        link_count += 1
            
            # 关联邻近页面的公式
            for eq in formulas:
                eq_page = eq.get('page', -1)
                if abs(eq_page - text_page) <= page_window:
                    existing = self.index.index['text_to_formulas'].get(chunk_id, [])
                    if eq['formula_id'] not in existing:
                        self.index.link_text_to_formula(chunk_id, eq['formula_id'])
                        link_count += 1
        
        print(f"[ContentLinker] 邻近度关联完成: {link_count} 个")


if __name__ == "__main__":
    # 测试代码
    from multimodal_index import MultimodalIndex
    
    # 创建测试数据
    index = MultimodalIndex()
    
    test_texts = [
        Document(
            page_content="如图1.1所示,Buck变换器的基本拓扑包括开关管、二极管和LC滤波器。",
            metadata={'source': 'test.pdf', 'page': 5}
        ),
        Document(
            page_content="输出纹波电压可以用公式V_ripple = I_out / (8*f*C)计算。",
            metadata={'source': 'test.pdf', 'page': 10}
        )
    ]
    
    test_figures = [
        {
            'figure_id': 'test_fig_1',
            'page': 5,
            'caption': '图1.1 Buck变换器电路',
            'image_path': '/path/to/fig1.png',
            'source': 'test.pdf'
        }
    ]
    
    test_formulas = [
        {
            'formula_id': 'test_eq_1',
            'page': 10,
            'text': 'V_ripple = I_out / (8*f*C)',
            'context': '输出纹波电压可以用公式',
            'image_path': '/path/to/eq1.png',
            'source': 'test.pdf'
        }
    ]
    
    # 添加到索引
    for fig in test_figures:
        index.add_figure(fig)
    for eq in test_formulas:
        index.add_formula(eq)
    
    # 执行关联
    linker = ContentLinker(index)
    linker.link_documents(test_texts, test_figures, test_formulas)
    
    # 打印结果
    index.print_statistics()
    
    print("\n测试完成")

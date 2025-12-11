"""
多模态内容索引
统一管理文本、图片、公式的索引和关联关系
"""
import json
from typing import List, Dict, Optional
from langchain_core.documents import Document
import hashlib
import os


class MultimodalIndex:
    """多模态内容索引"""
    
    def __init__(self, index_path: str = "./data_base_v3/multimodal_index.json"):
        """
        初始化多模态索引
        
        Args:
            index_path: 索引文件路径
        """
        self.index_path = index_path
        self.index = {
            'figures': {},  # figure_id -> metadata
            'formulas': {},  # formula_id -> metadata
            'text_to_figures': {},  # chunk_id -> [figure_ids]
            'text_to_formulas': {},  # chunk_id -> [formula_ids]
            'metadata': {
                'version': '1.0',
                'total_figures': 0,
                'total_formulas': 0,
                'total_links': 0
            }
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        
        # 尝试加载已有索引
        self.load()
        
        print(f"[MultimodalIndex] 初始化完成")
        print(f"  - 图片: {len(self.index['figures'])} 个")
        print(f"  - 公式: {len(self.index['formulas'])} 个")
        print(f"  - 关联: {len(self.index['text_to_figures']) + len(self.index['text_to_formulas'])} 个")
    
    def add_figure(self, figure_meta: Dict):
        """
        添加图片索引
        
        Args:
            figure_meta: 图片元数据字典
        """
        fig_id = figure_meta['figure_id']
        self.index['figures'][fig_id] = figure_meta
        self.index['metadata']['total_figures'] = len(self.index['figures'])
    
    def add_formula(self, formula_meta: Dict):
        """
        添加公式索引
        
        Args:
            formula_meta: 公式元数据字典
        """
        eq_id = formula_meta['formula_id']
        self.index['formulas'][eq_id] = formula_meta
        self.index['metadata']['total_formulas'] = len(self.index['formulas'])
    
    def link_text_to_figure(self, chunk_id: str, figure_id: str):
        """
        关联文本块与图片
        
        Args:
            chunk_id: 文本块ID
            figure_id: 图片ID
        """
        if chunk_id not in self.index['text_to_figures']:
            self.index['text_to_figures'][chunk_id] = []
        
        # 避免重复关联
        if figure_id not in self.index['text_to_figures'][chunk_id]:
            self.index['text_to_figures'][chunk_id].append(figure_id)
            self._update_link_count()
    
    def link_text_to_formula(self, chunk_id: str, formula_id: str):
        """
        关联文本块与公式
        
        Args:
            chunk_id: 文本块ID
            formula_id: 公式ID
        """
        if chunk_id not in self.index['text_to_formulas']:
            self.index['text_to_formulas'][chunk_id] = []
        
        # 避免重复关联
        if formula_id not in self.index['text_to_formulas'][chunk_id]:
            self.index['text_to_formulas'][chunk_id].append(formula_id)
            self._update_link_count()
    
    def get_related_figures(self, doc: Document) -> List[Dict]:
        """
        获取文档块关联的图片
        
        Args:
            doc: LangChain文档对象
            
        Returns:
            图片元数据列表
        """
        chunk_id = self._get_chunk_id(doc)
        fig_ids = self.index['text_to_figures'].get(chunk_id, [])
        
        # 返回完整的图片元数据
        figures = []
        for fid in fig_ids:
            if fid in self.index['figures']:
                figures.append(self.index['figures'][fid])
        
        return figures
    
    def get_related_formulas(self, doc: Document) -> List[Dict]:
        """
        获取文档块关联的公式
        
        Args:
            doc: LangChain文档对象
            
        Returns:
            公式元数据列表
        """
        chunk_id = self._get_chunk_id(doc)
        eq_ids = self.index['text_to_formulas'].get(chunk_id, [])
        
        # 返回完整的公式元数据
        formulas = []
        for eid in eq_ids:
            if eid in self.index['formulas']:
                formulas.append(self.index['formulas'][eid])
        
        return formulas
    
    def get_figure_by_id(self, figure_id: str) -> Optional[Dict]:
        """根据ID获取图片元数据"""
        return self.index['figures'].get(figure_id)
    
    def get_formula_by_id(self, formula_id: str) -> Optional[Dict]:
        """根据ID获取公式元数据"""
        return self.index['formulas'].get(formula_id)
    
    def search_figures_by_caption(self, keyword: str, source_filter: str = None) -> List[Dict]:
        """
        按 Caption 关键词搜索图片
        
        Args:
            keyword: 搜索关键词 (如 "Figure 10")
            source_filter: 可选，按文档名筛选
            
        Returns:
            匹配的图片元数据列表
        """
        results = []
        keyword_lower = keyword.lower()
        
        for fig_id, fig in self.index['figures'].items():
            caption = fig.get('caption', '')
            source = fig.get('source', '')
            
            if keyword_lower in caption.lower():
                if source_filter is None or source_filter.lower() in source.lower():
                    results.append(fig)
                    
        return results
    
    def get_figures_by_page(self, source: str, page: int) -> List[Dict]:
        """
        获取指定文档指定页面的所有图片
        
        Args:
            source: 文档名 (支持部分匹配)
            page: 页码
            
        Returns:
            该页面的图片列表
        """
        results = []
        source_lower = source.lower()
        
        for fig_id, fig in self.index['figures'].items():
            fig_source = fig.get('source', '')
            fig_page = fig.get('page', -1)
            
            if fig_page == page and source_lower in fig_source.lower():
                results.append(fig)
                
        return results
    
    def search_formulas_by_id(self, formula_num: str, source_filter: str = None) -> List[Dict]:
        """
        按公式编号搜索 (如 "3.26")
        
        Args:
            formula_num: 公式编号
            source_filter: 可选，按文档名筛选
            
        Returns:
            匹配的公式列表
        """
        results = []
        
        for eq_id, eq in self.index['formulas'].items():
            eq_text = eq.get('text', '')
            eq_context = eq.get('context', '')
            source = eq.get('source', '')
            
            # 检查编号是否在 text 或 context 中
            if formula_num in eq_text or formula_num in eq_context:
                if source_filter is None or source_filter.lower() in source.lower():
                    results.append(eq)
                    
        return results
    
    def _get_chunk_id(self, doc: Document) -> str:
        """
        生成文本块唯一ID
        
        基于source、page和内容哈希生成稳定的ID
        
        Args:
            doc: LangChain文档对象
            
        Returns:
            chunk_id字符串
        """
        meta = doc.metadata or {}
        source = meta.get('source', 'unknown')
        page = meta.get('page', 0)
        
        # 使用内容哈希作为ID的一部分,确保唯一性
        content_hash = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()[:8]
        
        # 提取文件名(不含路径)
        if source != 'unknown':
            source_name = os.path.basename(source)
        else:
            source_name = source
        
        return f"{source_name}_p{page}_{content_hash}"
    
    def _update_link_count(self):
        """更新关联计数"""
        total = len(self.index['text_to_figures']) + len(self.index['text_to_formulas'])
        self.index['metadata']['total_links'] = total
    
    def save(self):
        """保存索引到文件"""
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
            print(f"[MultimodalIndex] 索引已保存: {self.index_path}")
        except Exception as e:
            print(f"[MultimodalIndex] 保存索引失败: {e}")
    
    def load(self):
        """从文件加载索引"""
        if not os.path.exists(self.index_path):
            print(f"[MultimodalIndex] 索引文件不存在,使用空索引")
            return
        
        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                loaded_index = json.load(f)
                
                # 合并加载的索引(保留默认结构)
                self.index.update(loaded_index)
                
            print(f"[MultimodalIndex] 索引已加载: {self.index_path}")
        except Exception as e:
            print(f"[MultimodalIndex] 加载索引失败: {e}, 使用空索引")
    
    def clear(self):
        """清空索引"""
        self.index = {
            'figures': {},
            'formulas': {},
            'text_to_figures': {},
            'text_to_formulas': {},
            'metadata': {
                'version': '1.0',
                'total_figures': 0,
                'total_formulas': 0,
                'total_links': 0
            }
        }
        print("[MultimodalIndex] 索引已清空")
    
    def get_statistics(self) -> Dict:
        """获取索引统计信息"""
        stats = {
            'total_figures': len(self.index['figures']),
            'total_formulas': len(self.index['formulas']),
            'total_text_chunks_with_figures': len(self.index['text_to_figures']),
            'total_text_chunks_with_formulas': len(self.index['text_to_formulas']),
            'total_figure_links': sum(len(figs) for figs in self.index['text_to_figures'].values()),
            'total_formula_links': sum(len(eqs) for eqs in self.index['text_to_formulas'].values())
        }
        return stats
    
    def print_statistics(self):
        """打印索引统计信息"""
        stats = self.get_statistics()
        print("\n[MultimodalIndex] 索引统计:")
        print(f"  图片总数: {stats['total_figures']}")
        print(f"  公式总数: {stats['total_formulas']}")
        print(f"  关联图片的文本块: {stats['total_text_chunks_with_figures']}")
        print(f"  关联公式的文本块: {stats['total_text_chunks_with_formulas']}")
        print(f"  图片关联总数: {stats['total_figure_links']}")
        print(f"  公式关联总数: {stats['total_formula_links']}")


if __name__ == "__main__":
    # 测试代码
    index = MultimodalIndex()
    
    # 测试添加图片
    test_figure = {
        'figure_id': 'test_fig_1',
        'page': 5,
        'image_path': '/path/to/test_fig_1.png',
        'caption': '测试图片',
        'source': 'test.pdf'
    }
    index.add_figure(test_figure)
    
    # 测试添加公式
    test_formula = {
        'formula_id': 'test_eq_1',
        'page': 10,
        'image_path': '/path/to/test_eq_1.png',
        'text': 'V = IR',
        'source': 'test.pdf'
    }
    index.add_formula(test_formula)
    
    # 测试关联
    test_doc = Document(
        page_content="这是一个测试文本块",
        metadata={'source': 'test.pdf', 'page': 5}
    )
    chunk_id = index._get_chunk_id(test_doc)
    index.link_text_to_figure(chunk_id, 'test_fig_1')
    index.link_text_to_formula(chunk_id, 'test_eq_1')
    
    # 打印统计
    index.print_statistics()
    
    # 测试保存和加载
    index.save()
    print("\n测试完成")

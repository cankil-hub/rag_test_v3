
from typing import List, Dict

class LDOResearcher:
    """
    研究员：负责通过 RAG 获取信息
    """
    def __init__(self, rag_engine):
        self.rag = rag_engine

    def search_topology(self, keywords: str, source_filter: str = None) -> tuple:
        """
        搜索特定拓扑结构的资料
        
        Returns:
            (context_text, figure_paths, formula_paths)
        """
        filter_msg = f" (限定文档: {source_filter})" if source_filter else ""
        print(f"  [Researcher] 正在搜索: '{keywords}'{filter_msg} ...")
        
        # 使用 RAG 引擎的 retrieve_context 获取素材
        context, figure_paths, formula_paths = self.rag.retrieve_context(keywords, source_filter=source_filter)
        
        # 检查是否有图片
        if figure_paths:
            print(f"  [Researcher] ✓ 找到了 {len(figure_paths)} 张图片")
        else:
            print("  [Researcher] ⚠ 警告: 检索结果中没有图片")
            
        return context, figure_paths, formula_paths

    def get_formula_for_topology(self, topology_name: str) -> str:
        """搜索特定拓扑的计算公式"""
        query = f"design equations for {topology_name}"
        print(f"  [Researcher] 正在查找公式: '{query}' ...")
        return self.rag.retrieve_context(query)

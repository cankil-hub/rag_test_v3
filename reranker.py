"""
重排序模块 (Reranker)
使用交叉编码器对检索结果进行重排序,提高相关性
"""
from typing import List
from langchain_core.documents import Document


class SimpleReRanker:
    """简单的重排序器 - 基于关键词匹配"""
    
    def __init__(self):
        """初始化重排序器"""
        print("[ReRanker] 初始化简单重排序器")
    
    def rerank(
        self, 
        query: str, 
        docs: List[Document], 
        top_k: int = 10
    ) -> List[Document]:
        """
        对文档进行重排序
        
        Args:
            query: 查询文本
            docs: 文档列表
            top_k: 返回前K个文档
            
        Returns:
            重排序后的文档列表
        """
        if not docs:
            return []
        
        # 提取查询关键词
        query_terms = set(query.lower().split())
        
        # 计算每个文档的分数
        scored_docs = []
        for doc in docs:
            content = doc.page_content.lower()
            
            # 计算关键词匹配度
            matches = sum(1 for term in query_terms if term in content)
            
            # 计算TF (词频)
            tf_score = sum(content.count(term) for term in query_terms)
            
            # 综合分数
            score = matches * 2 + tf_score
            
            scored_docs.append((doc, score))
        
        # 按分数排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # 返回top_k
        reranked = [doc for doc, score in scored_docs[:top_k]]
        
        print(f"[ReRanker] 重排序完成: {len(docs)} -> {len(reranked)} 个文档")
        return reranked


# 可选: 使用CrossEncoder的高级重排序器
try:
    from sentence_transformers import CrossEncoder
    
    class CrossEncoderReRanker:
        """基于CrossEncoder的重排序器"""
        
        def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
            """
            初始化CrossEncoder重排序器
            
            Args:
                model_name: 模型名称
            """
            print(f"[ReRanker] 加载CrossEncoder模型: {model_name}")
            self.model = CrossEncoder(model_name)
            print("[ReRanker] CrossEncoder加载成功")
        
        def rerank(
            self, 
            query: str, 
            docs: List[Document], 
            top_k: int = 10
        ) -> List[Document]:
            """
            使用CrossEncoder对文档进行重排序
            
            Args:
                query: 查询文本
                docs: 文档列表
                top_k: 返回前K个文档
                
            Returns:
                重排序后的文档列表
            """
            if not docs:
                return []
            
            # 构建查询-文档对
            pairs = [[query, doc.page_content] for doc in docs]
            
            # 预测相关性分数
            scores = self.model.predict(pairs)
            
            # 按分数排序
            ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
            
            # 返回top_k
            reranked = [doc for doc, score in ranked[:top_k]]
            
            print(f"[ReRanker] CrossEncoder重排序完成: {len(docs)} -> {len(reranked)} 个文档")
            return reranked
    
    # 默认使用CrossEncoder
    ReRanker = CrossEncoderReRanker
    print("[ReRanker] 使用CrossEncoder重排序器")

except ImportError:
    # 如果没有安装sentence-transformers,使用简单重排序器
    ReRanker = SimpleReRanker
    print("[ReRanker] sentence-transformers未安装,使用简单重排序器")


if __name__ == "__main__":
    # 测试重排序器
    from langchain_core.documents import Document
    
    # 创建测试文档
    test_docs = [
        Document(page_content="Miller Compensation是一种常用的频率补偿技术"),
        Document(page_content="LDO电路设计需要考虑稳定性和瞬态响应"),
        Document(page_content="Miller补偿通过在放大器级间添加电容来改善相位裕度"),
        Document(page_content="Right-Half-Plane Zero会影响系统的稳定性"),
    ]
    
    # 测试查询
    query = "Miller Compensation工作原理"
    
    # 创建重排序器
    reranker = ReRanker()
    
    # 重排序
    reranked = reranker.rerank(query, test_docs, top_k=3)
    
    print(f"\n重排序结果:")
    for i, doc in enumerate(reranked, 1):
        print(f"{i}. {doc.page_content[:50]}...")

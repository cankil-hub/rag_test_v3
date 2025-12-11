"""
Embedding模型调用模块 (v3)
负责文本向量化
"""
from typing import List
from openai import OpenAI
from config import Config
from langchain_core.embeddings import Embeddings


class QwenEmbedding(Embeddings):
    """Qwen Embedding模型封装类"""

    def __init__(self, config = Config()):
        """
        初始化Embedding模型
        
        Args:
            config: 配置对象
        """
        self.embedding_config = config.get_embedding_config()

        self.client = OpenAI(
            api_key=self.embedding_config["api_key"],
            base_url=self.embedding_config["base_url"]
        )
    
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        for i, t in enumerate(texts):
            if not isinstance(t, str):
                raise TypeError(f"embed_documents: 第 {i} 个元素不是 str，而是 {type(t)}")

        embeddings: List[List[float]] = []

        for i in range(0, len(texts), 10):
            batch = texts[i : i + 10]

            resp = self.client.embeddings.create(
                model=self.embedding_config["model"],
                input=batch,
            )

            # OpenAI v1: resp.data 是 Embedding 对象列表，每个有 .embedding
            batch_vecs = [item.embedding for item in resp.data]
            embeddings.extend(batch_vecs)

        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        生成输入文本的 embedding.

        Args:
            texts (str): 要生成 embedding 的文本.

        Return:
            embeddings (List[float]): 输入文本的 embedding，一个浮点数值列表.
        """

        return self.embed_documents([text])[0]
    
    
    def get_embedding_dimension(self) -> int:
        """
        获取向量维度
        
        Returns:
            向量维度
        """
        try:
            test_vector = self.embed_query("test")
            return len(test_vector)
        except Exception as e:
            print(f"获取向量维度失败: {e}")
            return 0
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度(余弦相似度)
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数(0-1)
        """
        try:
            import numpy as np

            vec1 = self.embed_query(text1)
            vec2 = self.embed_query(text2)

            if not vec1 or not vec2:
                return 0.0
            
            # 计算余弦相似度
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)
            
            similarity = np.dot(vec1_np, vec2_np) / (
                np.linalg.norm(vec1_np) * np.linalg.norm(vec2_np)
            )
            
            return float(similarity)
        
        except Exception as e:
            print(f"计算相似度失败: {e}")
            return 0.0


if __name__ == "__main__":
    # 测试Embedding模块
    try:
        config = Config()
        embedding_model = QwenEmbedding(config)
        
        print("✓ Embedding模型初始化成功")
        
        # 测试单个文本向量化
        test_text = "这是一个测试文本"
        vector = embedding_model.embed_query(test_text)
        print(f"\n向量维度: {len(vector)}")
        print(f"向量前5个元素: {vector[:5]}")
        
        # 测试批量向量化
        test_texts = ["文本1", "文本2", "文本3"]
        vectors = embedding_model.embed_documents(test_texts)
        print(f"\n批量向量化成功, 共{len(vectors)}个向量")
        
        print("\n✓ Embedding模型测试完成")
        
    except Exception as e:
        print(f"✗ Embedding模型测试失败: {e}")

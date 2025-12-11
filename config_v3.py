"""
v3 配置模块
在不影响现有 v2 项目的前提下，为多模态 RAG 增加独立的配置入口。
"""
import os
from typing import Dict

from config import Config as BaseConfig


class ConfigV3:
    """v3 配置管理类"""

    def __init__(self, env_path: str = ".env"):
        # 复用已有 Config 加载 .env 和基础配置
        self._base = BaseConfig(env_path)

        # 文档处理配置（沿用 v2）
        self.documents_dir = self._base.documents_dir
        self.chunk_size = self._base.chunk_size
        self.chunk_overlap = self._base.chunk_overlap

        # v3 向量库配置（使用单独的持久化目录 / 集合名，避免和 v2 冲突）
        self.chroma_persist_directory = os.getenv(
            "V3_CHROMA_PERSIST_DIR", "./data_base_v3/chroma"
        )
        self.collection_name = os.getenv(
            "V3_COLLECTION_NAME", "rag_v3_knowledge_base"
        )

        # PDF 页图导出目录
        self.page_image_dir = os.getenv(
            "V3_PAGE_IMAGE_DIR", "./data_base_v3/page_images"
        )

        # Gemini 多模态模型配置
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        # 回答模型，建议使用 gemini-2.0-flash 或 gemini-2.5-flash
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        self._validate()

    # 基础配置透传（复用 Qwen Embedding 等）
    def get_embedding_config(self) -> Dict[str, str]:
        return self._base.get_embedding_config()

    def get_document_config(self) -> Dict[str, object]:
        return {
            "documents_dir": self.documents_dir,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }

    def get_vectorstore_config(self) -> Dict[str, str]:
        return {
            "persist_directory": self.chroma_persist_directory,
            "collection_name": self.collection_name,
        }

    def get_gemini_config(self) -> Dict[str, str]:
        return {
            "api_key": self.gemini_api_key,
            "model": self.gemini_model,
        }

    def _validate(self):
        # 对 v3 特有配置做最基本的校验；Embedding/LLM 的基础配置由 BaseConfig 负责
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY 未设置（v3 多模态需要）")



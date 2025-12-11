"""
配置管理模块 (v3)
负责从.env文件加载配置信息
"""
import os
from dotenv import load_dotenv
from typing import Optional


class Config:
    """配置管理类"""
    
    def __init__(self, env_path: str = ".env"):
        """
        初始化配置管理器
        
        Args:
            env_path: .env文件路径
        """
        self.env_path = env_path
        self._load_env()
        self._init_config()
    
    def _load_env(self):
        """加载.env文件"""
        if not os.path.exists(self.env_path):
            print(f"警告: 未找到.env文件: {self.env_path}")
            print("将使用环境变量或默认值")
            return
        load_dotenv(self.env_path)
    
    def _init_config(self):
        """初始化配置项"""
        # Embedding配置
        self.embedding_api_key = os.getenv("EMBEDDING_API_KEY")
        self.embedding_base_url = os.getenv("EMBEDDING_BASE_URL")
        self.embedding_model = os.getenv("EMBEDDING_MODEL")
        
        # 文档处理配置
        self.documents_dir = os.getenv("DOCUMENTS_DIR", "./documents")
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "500"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "50"))
        
        # 验证必要配置
        if not self.embedding_api_key:
            print("警告: EMBEDDING_API_KEY未设置")
        if not self.embedding_base_url:
            print("警告: EMBEDDING_BASE_URL未设置")
    
    def get_embedding_config(self) -> dict:
        """获取Embedding配置"""
        return {
            "api_key": self.embedding_api_key,
            "base_url": self.embedding_base_url,
            "model": self.embedding_model
        }
    
    def get_document_config(self) -> dict:
        """获取文档处理配置"""
        return {
            "documents_dir": self.documents_dir,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }


if __name__ == "__main__":
    # 测试配置模块
    try:
        config = Config()
        print("✓ 配置加载成功")
        print(f"Embedding模型: {config.embedding_model}")
        print(f"文档目录: {config.documents_dir}")
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")

"""
v3 向量数据库构建模块
复用 Qwen Embedding, 但使用独立的持久化目录与集合名, 供多模态 RAG 使用。
"""
import os
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredMarkdownLoader,
    PyMuPDFLoader,
    JSONLoader,
)
from langchain_chroma import Chroma
from langchain_core.documents import Document

from qwen_embedding import QwenEmbedding
from config_v3 import ConfigV3


class VectorStoreV3:
    """v3 向量数据库管理类"""

    def __init__(self, config: ConfigV3, embedding_model: QwenEmbedding):
        self.config = config
        self.embedding_model = embedding_model

        doc_cfg = config.get_document_config()
        self.documents_dir = doc_cfg["documents_dir"]
        self.chunk_size = int(doc_cfg["chunk_size"])
        self.chunk_overlap = int(doc_cfg["chunk_overlap"])

        vs_cfg = config.get_vectorstore_config()
        self.persist_directory = vs_cfg["persist_directory"]
        self.collection_name = vs_cfg["collection_name"]

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )

        self.vectorstore: Optional[Chroma] = None

    # 基础清洗逻辑与 v2 类似, 保证文本/元数据可用
    def clean_document_content(self, doc: Document) -> Document:
        if doc.page_content is None:
            doc.page_content = ""
        elif not isinstance(doc.page_content, str):
            doc.page_content = str(doc.page_content)

        doc.page_content = doc.page_content.strip()
        doc.page_content = doc.page_content.replace("\x00", "")
        doc.page_content = " ".join(doc.page_content.split())

        if not doc.page_content:
            doc.page_content = "[空文档]"

        if doc.metadata:
            cleaned = {}
            for k, v in doc.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    cleaned[k] = v
                elif v is not None:
                    cleaned[k] = str(v)
            doc.metadata = cleaned

        return doc

    def load_document(self, file_path: str) -> List[Document]:
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == ".txt":
                loader = TextLoader(file_path, encoding="utf-8")
            elif file_ext == ".md":
                loader = UnstructuredMarkdownLoader(file_path)
            elif file_ext == ".pdf":
                loader = PyMuPDFLoader(file_path)
            elif file_ext == ".json":
                loader = JSONLoader(
                    file_path,
                    jq_schema=".",
                    text_content=False,
                )
            else:
                print(f"[v3] 不支持的文件格式: {file_ext}")
                return []

            docs = loader.load()
            cleaned_docs: List[Document] = []
            for d in docs:
                try:
                    cleaned = self.clean_document_content(d)
                    if cleaned.page_content and cleaned.page_content.strip():
                        cleaned_docs.append(cleaned)
                except Exception as e:
                    print(f"[v3] 清理文档片段失败: {e}")
                    continue

            if cleaned_docs:
                print(f"[v3] 加载文档: {os.path.basename(file_path)}, 有效片段 {len(cleaned_docs)}")
            else:
                print(f"[v3] 文档无有效内容: {os.path.basename(file_path)}")

            return cleaned_docs

        except Exception as e:
            print(f"[v3] 加载文档失败 {file_path}: {e}")
            return []

    def load_documents_from_directory(self) -> List[Document]:
        if not os.path.exists(self.documents_dir):
            print(f"[v3] 文档目录不存在: {self.documents_dir}")
            return []

        all_docs: List[Document] = []
        exts = [".txt", ".md", ".pdf", ".json"]

        print(f"[v3] 开始加载文档目录: {self.documents_dir}")
        for root, _, files in os.walk(self.documents_dir):
            for f in files:
                if os.path.splitext(f)[1].lower() in exts:
                    fp = os.path.join(root, f)
                    docs = self.load_document(fp)
                    all_docs.extend(docs)

        print(f"[v3] 总共加载 {len(all_docs)} 个文档片段")
        return all_docs

    def split_documents(self, docs: List[Document]) -> List[Document]:
        if not docs:
            return []
        try:
            splitted = self.text_splitter.split_documents(docs)
            print(f"[v3] 文档切分完成: {len(docs)} -> {len(splitted)} 个片段")
            return splitted
        except Exception as e:
            print(f"[v3] 文档切分失败: {e}")
            return docs

    def build_vectorstore(self, force_rebuild: bool = False) -> bool:
        if os.path.exists(self.persist_directory) and not force_rebuild:
            print(f"[v3] 向量数据库已存在: {self.persist_directory}, 尝试加载")
            return self.load_vectorstore()

        print(f"[v3] 开始构建向量数据库: {self.persist_directory}")
        docs = self.load_documents_from_directory()
        if not docs:
            print("[v3] 没有可加载的文档")
            return False

        split_docs = self.split_documents(docs)
        if not split_docs:
            print("[v3] 文档切分失败")
            return False

        self.vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embedding_model,
            persist_directory=self.persist_directory,
            collection_name=self.collection_name,
        )

        print(f"[v3] 向量数据库构建成功: {self.persist_directory}")
        return True

    def load_vectorstore(self) -> bool:
        try:
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embedding_model,
                collection_name=self.collection_name,
            )
            print("[v3] 向量数据库加载成功")
            return True
        except Exception as e:
            print(f"[v3] 向量数据库加载失败: {e}")
            return False

    def search(
        self, 
        query: str, 
        k: int = 5,
        use_mmr: bool = True,
        fetch_k: int = 20,
        source_filter: str = None
    ) -> List[Document]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            k: 返回文档数量
            use_mmr: 是否使用MMR(最大边际相关性)减少冗余
            fetch_k: MMR模式下先获取的候选数量
            source_filter: 可选, 按文档名筛选 (支持部分匹配)
            
        Returns:
            文档列表
        """
        if not self.vectorstore:
            print("[v3] 向量数据库未初始化")
            return []

        try:
            # 先检索更多候选 (如果需要过滤，多取一些)
            fetch_count = k * 3 if source_filter else k
            
            if use_mmr and hasattr(self.vectorstore, "max_marginal_relevance_search"):
                # 使用MMR检索,减少冗余,提高多样性
                docs = self.vectorstore.max_marginal_relevance_search(
                    query,
                    k=fetch_count,
                    fetch_k=max(fetch_k, fetch_count * 2)
                )
                print(f"[v3] MMR检索完成: {len(docs)} 个文档")
            else:
                # 回退到相似度检索
                docs = self.vectorstore.similarity_search(query, k=fetch_count)
                print(f"[v3] 相似度检索完成: {len(docs)} 个文档")
            
            # 后过滤: 按 source 筛选
            if source_filter and docs:
                original_count = len(docs)
                docs = [d for d in docs if source_filter.lower() in d.metadata.get('source', '').lower()]
                print(f"[v3] 文档过滤 '{source_filter}': {original_count} -> {len(docs)} 个")
                
            # 最终截断到 k
            return docs[:k]
            
        except Exception as e:
            print(f"[v3] 检索失败: {e}")
            return []
    
    def expand_neighbors_by_page(
        self,
        docs: List[Document],
        page_window: int = 1,
        max_total: int = 12
    ) -> List[Document]:
        """
        扩展检索结果,包含相邻页面的内容
        
        Args:
            docs: 原始检索结果
            page_window: 前后扩展的页数
            max_total: 最大返回数量
            
        Returns:
            扩展后的文档列表
        """
        if not docs or not self.vectorstore:
            return docs
        
        expanded = []
        seen_content = set()  # 用于去重
        
        # 首先添加原始文档
        for doc in docs:
            content_hash = hash(doc.page_content)
            if content_hash not in seen_content:
                expanded.append(doc)
                seen_content.add(content_hash)
        
        # 然后查找相邻页面
        for doc in docs:
            source = doc.metadata.get('source')
            page = doc.metadata.get('page')
            
            if not source or page is None:
                continue
            
            # 查询相邻页面
            for offset in range(-page_window, page_window + 1):
                if offset == 0:  # 跳过当前页
                    continue
                    
                target_page = page + offset
                if target_page < 0:
                    continue
                
                try:
                    # 从向量库中查找同源同页的文档
                    neighbor_docs = self.vectorstore.similarity_search(
                        doc.page_content,  # 使用原文档内容作为查询
                        k=3,
                        filter={"source": source, "page": target_page}
                    )
                    
                    for neighbor_doc in neighbor_docs:
                        content_hash = hash(neighbor_doc.page_content)
                        if content_hash not in seen_content:
                            expanded.append(neighbor_doc)
                            seen_content.add(content_hash)
                            
                            if len(expanded) >= max_total:
                                print(f"[v3] 邻近扩展完成: {len(docs)} -> {len(expanded)} 个文档")
                                return expanded
                except Exception as e:
                    # 如果filter不支持,跳过
                    continue
        

        print(f"[v3] 邻近扩展完成: {len(docs)} -> {len(expanded)} 个文档")
        return expanded[:max_total]

    def delete_document_by_source(self, filename: str) -> bool:
        """
        根据源文件名删除文档(用于增量更新)
        """
        if not self.vectorstore:
            # 尝试加载
            if not self.load_vectorstore():
                return False
                
        try:
            # Chroma仅支持根据ID或Metadata删除
            # 我们需要构建一个包含完整路径的source filter
            # 假设filename只是文件名，我们需要模糊匹配或遍历
            # 更稳妥的是外部传入完整路径，或者这里做路径匹配
            
            # 为了安全，我们先查一下
            # 注意: Chroma的get不支持复杂filter，但在delete里可以用where
            print(f"[v3] 尝试删除旧文档: {filename}")
            
            # 构造filter: source以filename结尾 (Chroma不直接支持endswith)
            # 所以最好是传入准确的source路径。如果只传文件名，需要先遍历找到完整路径
            
            # 这里我们假设外部负责传入正确的完整路径，或者我们在metadata里存了filename
            # 如果只给 'LDO.pdf'，但存储的是 'd:/.../LDO.pdf'
            
            # 策略: 先get所有metadatas，找到匹配的ID，然后用ID删除
            data = self.vectorstore.get(include=["metadatas"])
            ids_to_delete = []
            
            for i, meta in enumerate(data['metadatas']):
                source = meta.get('source', '')
                if source.endswith(filename) or os.path.basename(source) == filename:
                    ids_to_delete.append(data['ids'][i])
            
            if ids_to_delete:
                print(f"[v3] 找到 {len(ids_to_delete)} 个旧片段，准备删除...")
                # 分批删除防止超限
                batch_size = 500
                for i in range(0, len(ids_to_delete), batch_size):
                    batch_ids = ids_to_delete[i:i+batch_size]
                    self.vectorstore.delete(ids=batch_ids)
                print(f"[v3] 删除完成")
                return True
            else:
                print(f"[v3] 未找到旧文档，无需删除")
                return True
                
        except Exception as e:
            print(f"[v3] 删除文档失败: {e}")
            return False

    def add_document(self, file_path: str) -> bool:
        """
        添加单个文档(用于增量更新)
        """
        if not self.vectorstore:
            # 如果不存在，尝试初始化一个新的(如果目录空的话)或者加载
            if not self.load_vectorstore():
                 # 无法加载，尝试全新构建一个只包含此文件的库? 
                 # 不，增量更新前提是库最好存在。如果不存在，就等于rebuild单文件
                 print(f"[v3] 向量库未初始化，尝试创建新库...")
                 # 初始化一个空的Chroma? Chroma.from_documents需要文档
                 pass

        try:
            print(f"[v3] 增量添加文档: {file_path}")
            docs = self.load_document(file_path)
            if not docs:
                return False
                
            split_docs = self.split_documents(docs)
            if not split_docs:
                return False
            
            if self.vectorstore:
                self.vectorstore.add_documents(split_docs)
            else:
                # 只有这一个文件的新库
                self.vectorstore = Chroma.from_documents(
                    documents=split_docs,
                    embedding=self.embedding_model,
                    persist_directory=self.persist_directory,
                    collection_name=self.collection_name,
                )
            
            print(f"[v3] 添加成功: {len(split_docs)} 个片段")
            return True
            
        except Exception as e:
            print(f"[v3] 添加文档失败: {e}")
            return False

    def get_existing_sources(self) -> List[str]:
        """获取所有已索引的源文件名"""
        if not self.vectorstore:
            # 尝试加载
            if not self.load_vectorstore():
                return []
        
        try:
            # 获取所有元数据
            data = self.vectorstore.get(include=["metadatas"])
            seen = set()
            for meta in data['metadatas']:
                source = meta.get('source', '')
                if source:
                    seen.add(os.path.basename(source))
            return list(seen)
        except Exception as e:
            print(f"[v3] 获取源文件列表失败: {e}")
            return []

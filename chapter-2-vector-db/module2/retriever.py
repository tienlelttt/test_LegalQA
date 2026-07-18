from abc import abstractmethod
from typing import List, Dict, Any
from shared.interfaces import RetrieverInterface
from shared.models.schemas import Chunk

def dict_to_chunk(res: Dict[str, Any]) -> Chunk:
    """Helper để convert payload từ DB sang Chunk"""
    payload = res.get("payload", res)
    return Chunk(
        chunk_id=payload.get('chunk_id', payload.get('id', 'unknown')),
        content=payload.get('text', payload.get('content', '')),
        parent_id=payload.get('parent_id', ''),
        chunk_type=payload.get('chunk_type', 'DIEU'),
        metadata={
            "document_id": payload.get('document_id', ''),
            "dieu_so": payload.get('dieu_so', ''),
            "khoan_so": payload.get('khoan_so', ''),
            "diem": payload.get('diem', ''),
            "ten_van_ban": payload.get('ten_van_ban', ''),
            "so_hieu": payload.get('so_hieu', ''),
            "trang_thai": payload.get('trang_thai', 'effective')
        }
    )

class BaseRetriever(RetrieverInterface):
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5, filters: dict = None) -> List[Chunk]:
        pass

    @abstractmethod
    def fetch_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        pass

class DenseRetriever(BaseRetriever):
    def __init__(self, vector_store, embedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 5, filters: dict = None) -> List[Chunk]:
        query_vector = self.embedder.embed_text(query)
        raw_results = self.vector_store.search(query_vector, top_k=top_k)
        return [dict_to_chunk(r) for r in raw_results]

    def fetch_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        return []

class SparseRetriever(BaseRetriever):
    def __init__(self, sparse_indexer):
        self.sparse_indexer = sparse_indexer

    def retrieve(self, query: str, top_k: int = 5, filters: dict = None) -> List[Chunk]:
        raw_results = self.sparse_indexer.search(query, top_k=top_k)
        return [dict_to_chunk(r) for r in raw_results]

    def fetch_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        return []

class GraphRetriever(BaseRetriever):
    def __init__(self, graph_store):
        self.graph_store = graph_store

    def retrieve(self, query: str, top_k: int = 5, filters: dict = None) -> List[Chunk]:
        # Trong thực tế, cần có LLM để trích xuất entity
        return []

    def fetch_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        return []

class HybridRetriever(BaseRetriever):
    def __init__(self, dense_retriever: DenseRetriever, sparse_retriever: SparseRetriever, graph_retriever: GraphRetriever):
        self.dense_retriever = dense_retriever
        self.sparse_retriever = sparse_retriever
        self.graph_retriever = graph_retriever

    def retrieve(self, query: str, top_k: int = 5, filters: dict = None) -> List[Chunk]:
        # Thực thi song song (giả lập bằng đồng bộ)
        dense_results = self.dense_retriever.retrieve(query, top_k=top_k, filters=filters)
        sparse_results = self.sparse_retriever.retrieve(query, top_k=top_k, filters=filters)
        # graph_results = self.graph_retriever.retrieve(query, top_k=top_k)
        
        # Reciprocal Rank Fusion (RRF) - Mô phỏng việc trộn kết quả
        combined_dict = {}
        
        def apply_rrf(results: List[Chunk], k_param=60):
            for rank, chunk in enumerate(results):
                chunk_id = chunk.chunk_id
                if not chunk_id or chunk_id == 'unknown':
                    continue
                score = 1.0 / (k_param + rank + 1)
                if chunk_id not in combined_dict:
                    combined_dict[chunk_id] = {"score": 0.0, "chunk": chunk}
                combined_dict[chunk_id]["score"] += score
                
        apply_rrf(dense_results)
        apply_rrf(sparse_results)
        
        # Sort by combined RRF score
        final_results = sorted(combined_dict.values(), key=lambda x: x["score"], reverse=True)
        return [x["chunk"] for x in final_results][:top_k]

    def fetch_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        return self.dense_retriever.fetch_by_ids(chunk_ids)

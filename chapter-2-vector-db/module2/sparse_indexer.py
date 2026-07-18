from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSparseIndexer(ABC):
    @abstractmethod
    def insert_chunks(self, texts: List[str], payloads: List[Dict[str, Any]], ids: List[int]) -> None:
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        pass

class BM25SparseIndexer(BaseSparseIndexer):
    """
    Simulation Layer cho BM25 / Qdrant Sparse.
    Sử dụng dictionary tĩnh hoặc BM25 đơn giản (như rank_bm25 nếu cài đặt)
    để mô phỏng kết quả exact match thay vì Qdrant/Elasticsearch thực.
    """
    def __init__(self):
        self.documents = []
        self.payloads = []
        self.ids = []

    def insert_chunks(self, texts: List[str], payloads: List[Dict[str, Any]], ids: List[int]) -> None:
        self.documents.extend(texts)
        self.payloads.extend(payloads)
        self.ids.extend(ids)
        print(f"[SparseIndexer] Đã giả lập lập chỉ mục BM25 cho {len(texts)} chunks.")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Mô phỏng tìm kiếm bằng string contain (chỉ dùng cho mục đích Development)
        results = []
        query_terms = query.lower().split()
        
        for idx, (doc, payload) in enumerate(zip(self.documents, self.payloads)):
            doc_lower = doc.lower()
            # Tính điểm đơn giản = số từ khóa trùng khớp
            score = sum(1 for term in query_terms if term in doc_lower)
            if score > 0:
                results.append({
                    "score": float(score),
                    "payload": payload,
                    "id": self.ids[idx]
                })
                
        # Sắp xếp theo score giảm dần
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

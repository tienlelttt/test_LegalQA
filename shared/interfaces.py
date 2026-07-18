from abc import ABC, abstractmethod
from typing import List
from shared.models.schemas import Chunk

class RetrieverInterface(ABC):
    """
    Interface chuẩn cho các bộ tìm kiếm (Retriever).
    Bất kỳ Retriever nào (Dense, Sparse, Hybrid) cũng phải tuân thủ việc
    nhận vào một câu truy vấn (query) và trả về một danh sách các Chunk.
    """
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5, filters: dict = None) -> List[Chunk]:
        pass

    @abstractmethod
    def fetch_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        """Lấy danh sách các chunk dựa trên ID (dùng để khôi phục parent chunk)."""
        pass

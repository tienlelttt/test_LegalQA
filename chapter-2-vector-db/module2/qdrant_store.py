import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

class LegalVectorStore:
    """
    Quản lý kết nối và thao tác với Qdrant Vector Database.
    """
    def __init__(self, location: str = ":memory:", collection_name: str = "legal_chunks", vector_size: int = 384):
        """
        Khởi tạo Qdrant Client.
        :param location: ":memory:" để chạy trên RAM, hoặc đường dẫn thư mục để lưu disk, hoặc URL server.
        :param collection_name: Tên collection.
        :param vector_size: Kích thước vector (phụ thuộc vào mô hình Embedding).
        """
        self.client = QdrantClient(location)
        self.collection_name = collection_name
        self.vector_size = vector_size
        
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """
        Tạo collection nếu chưa tồn tại.
        """
        if not self.client.collection_exists(collection_name=self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest.VectorParams(
                    size=self.vector_size, 
                    distance=rest.Distance.COSINE
                ),
            )
            print(f"Tạo collection mới: {self.collection_name}")
        else:
            print(f"Collection {self.collection_name} đã tồn tại.")

    def insert_chunks(self, vectors: List[List[float]], payloads: List[Dict[str, Any]], ids: Optional[List[str]] = None):
        """
        Thêm các chunks (vector + metadata) vào Qdrant.
        """
        if len(vectors) != len(payloads):
            raise ValueError("Số lượng vectors và payloads phải bằng nhau.")
            
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
            
        points = [
            rest.PointStruct(id=point_id, vector=vector, payload=payload)
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"Đã insert {len(points)} chunks vào Qdrant.")

    def search(self, query_vector: List[float], top_k: int = 5, filter_conditions: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Tìm kiếm các chunk gần nhất (KNN search).
        """
        # Hỗ trợ bộ lọc metadata đơn giản (nếu cần thiết ở giai đoạn 2)
        qdrant_filter = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                must_conditions.append(
                    rest.FieldCondition(
                        key=key,
                        match=rest.MatchValue(value=value)
                    )
                )
            qdrant_filter = rest.Filter(must=must_conditions)

        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=top_k,
            with_payload=True
        ).points

        
        results = []
        for hit in search_result:
            results.append({
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            })
            
        return results

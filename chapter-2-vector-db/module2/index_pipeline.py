from typing import List, Any
from shared.models.schemas import LegalDocument, Chunk

class IndexPipeline:
    """
    Luồng chuẩn hóa: Chunk -> Metadata -> Dense -> Sparse -> Graph
    """
    def __init__(self, embedder: Any, vector_store: Any, sparse_indexer: Any, graph_store: Any):
        self.embedder = embedder
        self.vector_store = vector_store
        self.sparse_indexer = sparse_indexer
        self.graph_store = graph_store

    def run(self, document: LegalDocument, chunks: List[Chunk]):
        print(f"Bắt đầu Index Pipeline cho văn bản {document.metadata.document_id}...")
        
        # 1. Chuẩn bị dữ liệu
        texts = []
        payloads = []
        ids = []
        for i, c in enumerate(chunks):
            texts.append(c.content)
            payloads.append({
                "chunk_type": c.chunk_type,
                "chunk_id": c.chunk_id,
                "text": c.content,
                "dieu_so": c.metadata.get("dieu_id", ""),
                "title": document.metadata.title,
                "status": document.metadata.status
            })
            ids.append(i)

        # 2. Dense Indexing
        print("Đang tạo Dense Embeddings...")
        vectors = self.embedder.embed_batch(texts)
        self.vector_store.insert_chunks(vectors=vectors, payloads=payloads, ids=ids)
        
        # 3. Sparse Indexing
        print("Đang tạo Sparse Index...")
        self.sparse_indexer.insert_chunks(texts=texts, payloads=payloads, ids=ids)
        
        # 4. Graph Indexing
        print("Đang tạo Knowledge Graph...")
        # Tạo node Văn bản
        doc_id = document.metadata.document_id or "UNKNOWN"
        self.graph_store.add_node(
            node_id=doc_id, 
            label="VanBan", 
            properties={"title": document.metadata.title, "status": document.metadata.status}
        )
        
        # Tạo các relation viện dẫn
        for citation in document.metadata.citations:
            # Mô phỏng đơn giản tạo cạnh CĂN CỨ
            self.graph_store.add_edge(source_id=doc_id, target_id=citation, relationship="CAN_CU")
            
        print("Hoàn tất Index Pipeline!")

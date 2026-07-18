import sys
import os
import io

# Add parent directory to sys.path to allow importing from 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Type assertion to avoid Pyright complaining about reconfigure missing on raw TextIO
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')

from shared.models.schemas import LegalDocument, Chunk, Metadata
from module2.embedder import LegalEmbedder
from module2.qdrant_store import LegalVectorStore
from module2.sparse_indexer import BM25SparseIndexer
from module2.graph_store import MemoryGraphRepository
from module2.index_pipeline import IndexPipeline
from module2.retriever import DenseRetriever, SparseRetriever, GraphRetriever, HybridRetriever


def main():
    print("="*60)
    print("DEMO: MODULE 2 VECTOR DB & HYBRID RETRIEVAL (MOCK DATA)")
    print("="*60)

    print("\n[1] Tạo Mock Data...")
    metadata = Metadata(
        document_id="123/2024",
        title="Luật thử nghiệm Demo 2",
        status="effective",
        citations=[]
    )
    doc = LegalDocument(metadata=metadata)
    
    chunks = [
        Chunk(chunk_id="c1", parent_id="123/2024", chunk_type="DIEU", content="Nội dung điều 1 về sở hữu", metadata={"dieu_id": "dieu_1"}),
        Chunk(chunk_id="c2", parent_id="123/2024", chunk_type="DIEU", content="Điều 2 quy định về đất đai", metadata={"dieu_id": "dieu_2"})
    ]
    
    print("\n[2] Khởi tạo các Store & Indexer...")
    vector_store = LegalVectorStore(location=":memory:", collection_name="demo2_collection", vector_size=384)
    embedder = LegalEmbedder(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    sparse_indexer = BM25SparseIndexer()
    graph_store = MemoryGraphRepository()

    print("\n[3] Chạy Index Pipeline...")
    pipeline = IndexPipeline(embedder, vector_store, sparse_indexer, graph_store)
    pipeline.run(doc, chunks)
    
    print("\n[4] Thiết lập Hybrid Retriever...")
    dense_r = DenseRetriever(vector_store, embedder)
    sparse_r = SparseRetriever(sparse_indexer)
    graph_r = GraphRetriever(graph_store)
    hybrid_retriever = HybridRetriever(dense_r, sparse_r, graph_r)

    print("\n[5] Thử nghiệm truy vấn (Retrieval)...")
    queries = [
        "sở hữu",
        "đất đai"
    ]
    
    for q in queries:
        print(f"\nCâu hỏi: '{q}'")
        results = hybrid_retriever.retrieve(q, top_k=2)
        for idx, res in enumerate(results):
            dieu_so = res.metadata.get('dieu_so', '')
            text = res.content[:100] + "..."
            print(f"  Top {idx+1} ({dieu_so}): {text}")

if __name__ == "__main__":
    main()

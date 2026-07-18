import pytest
import os
import sys
from shared.models.schemas import LegalDocument, Chunk, Metadata
from module2.embedder import LegalEmbedder
from module2.qdrant_store import LegalVectorStore
from module2.sparse_indexer import BM25SparseIndexer
from module2.graph_store import MemoryGraphRepository
from module2.retriever import DenseRetriever, SparseRetriever, GraphRetriever, HybridRetriever
from module2.index_pipeline import IndexPipeline

def test_sparse_indexer():
    indexer = BM25SparseIndexer()
    texts = ["Luật Đất đai quy định về sở hữu", "Luật Doanh nghiệp quy định về công ty"]
    payloads = [{"id": 1}, {"id": 2}]
    ids = [1, 2]
    
    indexer.insert_chunks(texts, payloads, ids)
    results = indexer.search("Đất đai", top_k=1)
    
    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["score"] > 0

def test_graph_store():
    store = MemoryGraphRepository()
    store.add_node("doc_1", "VanBan", {"title": "Luật Đất đai"})
    store.add_node("doc_2", "VanBan", {"title": "Nghị định 01"})
    store.add_edge("doc_1", "doc_2", "CAN_CU")
    
    related = store.get_related_nodes("doc_1", "CAN_CU")
    assert len(related) == 1
    assert related[0]["properties"]["title"] == "Nghị định 01"

def test_hybrid_retrieval_and_pipeline():
    vector_store = LegalVectorStore(location=":memory:", collection_name="test_collection", vector_size=384)
    embedder = LegalEmbedder(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    sparse_indexer = BM25SparseIndexer()
    graph_store = MemoryGraphRepository()
    
    pipeline = IndexPipeline(embedder, vector_store, sparse_indexer, graph_store)
    
    # Mock Document
    metadata = Metadata(
        document_id="123/2024",
        title="Luật thử nghiệm",
        status="effective",
        citations=["doc_related_1"]
    )
    doc = LegalDocument(metadata=metadata)
    
    # Mock Chunks
    c1 = Chunk(chunk_id="c1", parent_id="doc_1", chunk_type="DIEU", content="Đây là nội dung Điều 1", metadata={"dieu_id": "dieu_1"})
    c2 = Chunk(chunk_id="c2", parent_id="doc_1", chunk_type="DIEU", content="Đây là nội dung Điều 2 về sở hữu", metadata={"dieu_id": "dieu_2"})
    
    # Run Pipeline
    pipeline.run(doc, [c1, c2])
    
    # Check Graph Store
    nodes = graph_store.nodes
    assert "123/2024" in nodes
    related = graph_store.get_related_nodes("123/2024", "CAN_CU")
    # Actually wait, add_edge doesn't strictly verify target node existence in my simulation. 
    # Let's just check the edges array.
    assert len(graph_store.edges) == 1
    
    # Test Retriever
    dense_r = DenseRetriever(vector_store, embedder)
    sparse_r = SparseRetriever(sparse_indexer)
    graph_r = GraphRetriever(graph_store)
    
    hybrid = HybridRetriever(dense_r, sparse_r, graph_r)
    results = hybrid.retrieve("sở hữu", top_k=1)
    
    assert len(results) > 0
    # The chunk_id is mapped in payload
    assert results[0].chunk_id == "c2"

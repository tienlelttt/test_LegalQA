import pytest
import os
import sys

from shared.paths import get_mock_file
from src.cleaner import LegalCleaner
from src.parser import LegalStructureParser
from src.extractor import RegexMetadataExtractor, MockLLMMetadataExtractor
from src.chunker import AdaptiveChunker

from module2.embedder import LegalEmbedder
from module2.qdrant_store import LegalVectorStore
from module2.sparse_indexer import BM25SparseIndexer
from module2.graph_store import MemoryGraphRepository
from module2.index_pipeline import IndexPipeline
from module2.retriever import DenseRetriever, SparseRetriever, GraphRetriever, HybridRetriever

def test_full_e2e_pipeline():
    # ---------------------------------------------------------
    # CHAPTER 1: Parsing & Chunking
    # ---------------------------------------------------------
    with open(get_mock_file("luat_dat_dai.txt"), "r", encoding="utf-8") as f:
        raw_text = f.read()

    # 1. Clean
    cleaner = LegalCleaner()
    cleaned_text = cleaner.clean(raw_text)

    # 2. Parse
    parser = LegalStructureParser()
    doc = parser.parse(cleaned_text)

    # 3. Extract Metadata
    base_extractor = RegexMetadataExtractor()
    extractor = MockLLMMetadataExtractor(base_extractor)
    doc = extractor.extract_metadata(cleaned_text, doc)
    
    # Assert Document Schema & Metadata integrity
    assert doc.metadata.document_id == "31/2024/QH15"
    assert "effective" in doc.metadata.status or "Luật Đất đai" in doc.metadata.title

    # 4. Chunk
    chunker = AdaptiveChunker(max_words=200)
    chunks = chunker.chunk(doc)
    
    assert len(chunks) > 0
    # Verify Chunk ID and Parent ID
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_id is not None
        assert chunk.parent_id is not None
        assert chunk.chunk_type in ["DIEU", "KHOAN", "DIEM"]

    # ---------------------------------------------------------
    # CHAPTER 2: Indexing & Vector DB
    # ---------------------------------------------------------
    
    vector_store = LegalVectorStore(location=":memory:", collection_name="e2e_test", vector_size=384)
    embedder = LegalEmbedder(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    sparse_indexer = BM25SparseIndexer()
    graph_store = MemoryGraphRepository()

    # Create Pipeline
    pipeline = IndexPipeline(embedder, vector_store, sparse_indexer, graph_store)
    
    # Execute Pipeline
    pipeline.run(doc, chunks)
    
    # ---------------------------------------------------------
    # CHAPTER 2: Retrieval Verification
    # ---------------------------------------------------------
    
    dense_r = DenseRetriever(vector_store, embedder)
    sparse_r = SparseRetriever(sparse_indexer)
    graph_r = GraphRetriever(graph_store)
    
    hybrid = HybridRetriever(dense_r, sparse_r, graph_r)
    
    # Retrieve
    results = hybrid.retrieve("sở hữu toàn dân", top_k=2)
    
    assert len(results) > 0
    top_result = results[0]
    
    # Ensure retrieval contains schema payload correctly
    assert top_result.chunk_id is not None
    assert top_result.content != ""
    
    # Check that knowledge graph stored the relations
    related_docs = graph_store.get_related_nodes(doc.metadata.document_id, "CAN_CU")
    assert len(graph_store.nodes) >= 1


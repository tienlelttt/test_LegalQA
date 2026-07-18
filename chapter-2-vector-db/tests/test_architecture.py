import pytest
import os
import sys
import ast

chapter_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
from shared.models.schemas import LegalDocument, Chunk, Metadata
from module2.embedder import LegalEmbedder
from module2.qdrant_store import LegalVectorStore
from module2.sparse_indexer import BM25SparseIndexer
from module2.graph_store import Neo4jRepository
from module2.index_pipeline import IndexPipeline

def test_migration_verification():
    """
    Xác minh việc thay thế MemoryGraphRepository bằng Neo4jRepository
    không làm hỏng pipeline hiện tại (Dependency Inversion / Liskov Substitution).
    """
    vector_store = LegalVectorStore(location=":memory:", collection_name="migration_test", vector_size=384)
    embedder = LegalEmbedder(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    sparse_indexer = BM25SparseIndexer()
    
    # Use Neo4jRepository stub instead of MemoryGraphRepository
    graph_store = Neo4jRepository()

    # IndexPipeline should accept it seamlessly since it depends on GraphRepository Interface
    pipeline = IndexPipeline(embedder, vector_store, sparse_indexer, graph_store)
    
    # Mock Data
    metadata = Metadata(
        document_id="123/2024",
        title="Luật Kiểm Thử Migration",
        status="effective",
        citations=["doc_related_1"]
    )
    doc = LegalDocument(metadata=metadata)
    
    c1 = Chunk(chunk_id="c1", parent_id="123/2024", chunk_type="DIEU", content="Điều 1 migration", metadata={"dieu_id": "dieu_1"})
    
    # Run pipeline with new GraphStore
    pipeline.run(doc, [c1])
    
    # Verify the mock Neo4jRepository successfully ingested the node
    assert len(graph_store._nodes) > 0
    assert "123/2024" in graph_store._nodes

def test_dependency_verification():
    """
    Xác minh Chapter 2 không phụ thuộc trực tiếp vào Chapter 1.
    Tất cả các schemas phải được import từ 'shared/'.
    """
    module2_path = os.path.join(chapter_dir, "module2")
    python_files = []
    
    for root, dirs, files in os.walk(module2_path):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
                
    violations = []
    
    for filepath in python_files:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("src.") or alias.name == "src":
                        violations.append(f"{os.path.basename(filepath)} imports {alias.name}")
                    if alias.name.startswith("chapter_1"):
                        violations.append(f"{os.path.basename(filepath)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module.startswith("src") or node.module.startswith("chapter_1")):
                    violations.append(f"{os.path.basename(filepath)} imports from {node.module}")

    # Nếu có vi phạm, test sẽ fail và in ra danh sách vi phạm
    assert len(violations) == 0, f"Dependency Violation Detected: {violations}"


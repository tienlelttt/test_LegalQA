import sys
import os
import io

# Type assertion to avoid Pyright complaining about reconfigure missing on raw TextIO
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')

# Inject chapter paths into sys.path to resolve module2, src, module3, etc.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
for chapter in ["chapter-1-parsing", "chapter-2-vector-db", "chapter-3-query-pipeline"]:
    chapter_path = os.path.join(PROJECT_ROOT, chapter)
    if chapter_path not in sys.path:
        sys.path.insert(0, chapter_path)

from module2.embedder import LegalEmbedder
from module2.qdrant_store import LegalVectorStore
from module2.sparse_indexer import BM25SparseIndexer
from module2.graph_store import MemoryGraphRepository
from module2.index_pipeline import IndexPipeline
from module2.retriever import DenseRetriever, SparseRetriever, GraphRetriever, HybridRetriever

from src.ingestor import MockPyMuPDFIngestor
from src.parser import LegalStructureParser
from src.chunker import AdaptiveChunker
from src.cleaner import LegalCleaner
from src.extractor import RegexMetadataExtractor, MockLLMMetadataExtractor
from shared.paths import get_mock_file

ingestor = MockPyMuPDFIngestor()
MOCK_LUAT_DAT_DAI = ingestor.read_text(str(get_mock_file("luat_dat_dai.txt")))

def main():
    print("="*60)
    print("DEMO END-TO-END: HYBRID RETRIEVAL & INDEX PIPELINE")
    print("="*60)

    print("\n[1] Parsing & Chunking (Module 1)...")
    cleaner = LegalCleaner()
    cleaned = cleaner.clean(MOCK_LUAT_DAT_DAI)
    
    parser = LegalStructureParser()
    doc = parser.parse(cleaned)
    
    extractor = MockLLMMetadataExtractor(RegexMetadataExtractor())
    doc = extractor.extract_metadata(cleaned, doc)
    
    chunker = AdaptiveChunker(max_words=200)
    chunks = chunker.chunk(doc)
    
    print("\n[2] Khởi tạo các Store & Indexer...")
    vector_store = LegalVectorStore(location=":memory:", collection_name="luat_dat_dai_demo", vector_size=384)
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
        "Sở hữu đất đai thuộc về ai?",
        "Trách nhiệm của nhà nước đối với người sử dụng đất?"
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

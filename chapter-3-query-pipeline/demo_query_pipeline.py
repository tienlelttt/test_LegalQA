import sys
import io

# Xử lý encoding console
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')

import os
# Inject project root to sys.path so 'shared' and other chapters are resolvable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    
for chapter in ["chapter-1-parsing", "chapter-2-vector-db", "chapter-3-query-pipeline"]:
    chapter_path = os.path.join(PROJECT_ROOT, chapter)
    if chapter_path not in sys.path:
        sys.path.insert(0, chapter_path)

# Giả lập import các module từ chapter 1 và 2 (Mock Data)
from module3.orchestrator import QueryOrchestrator, QueryPipeline
from module3.query_understanding import QueryNormalizer, RuleBasedQueryRewriter
from module3.prompt_builder import RetrievalContextBuilder, ContextWindowManager, PromptBuilder
from module3.reranker import MockReranker
from module3.generator import MockLLMGenerator
from module3.verifier import VerificationPipeline, CitationVerifier, MockGroundednessVerifier, HallucinationDetectionVerifier, ConfidenceScoringVerifier, RuleBasedScoringStrategy
from module3.planner import RuleBasedPlanner
from module3.expansion import LLMQueryExpander
from module3.router import LLMRouter
from shared.config.settings import settings

from shared.interfaces import RetrieverInterface
from shared.models.schemas import Chunk

# Mock 1 Retriever đơn giản trả về dữ liệu mẫu thay vì cắm DB thật
class MockHybridRetriever(RetrieverInterface):
    def retrieve(self, query: str, top_k: int = 5, filters: dict = None):
        # Trả về format List[Chunk] theo đúng chuẩn RetrieverInterface
        chunks = [
            Chunk(
                chunk_id='chunk_1',
                content='Đất đai thuộc sở hữu toàn dân do Nhà nước đại diện chủ sở hữu.',
                parent_id='doc_1',
                chunk_type='DIEU',
                metadata={
                    'dieu_so': 'dieu_1',
                    'ten_van_ban': 'Luật Đất Đai',
                    'so_hieu': '31/2024/QH15',
                    'trang_thai': 'effective'
                }
            ),
            Chunk(
                chunk_id='chunk_old',
                content='Luật cũ năm 1993 quy định...',
                parent_id='doc_old',
                chunk_type='DIEU',
                metadata={
                    'dieu_so': 'dieu_2',
                    'ten_van_ban': 'Luật Đất Đai Cũ',
                    'so_hieu': '1993/QH',
                    'trang_thai': 'hết_hiệu_lực'
                }
            )
        ]
        
        # Apply filters
        if filters:
            if "exclude_trang_thai" in filters:
                chunks = [c for c in chunks if c.metadata.get("trang_thai", "") != filters["exclude_trang_thai"]]
            if "trang_thai" in filters:
                chunks = [c for c in chunks if c.metadata.get("trang_thai", "") == filters["trang_thai"]]
        
        return chunks

    def fetch_by_ids(self, chunk_ids):
        # Mock fetch_by_ids trả về parent chunks (các Điều trọn vẹn)
        mock_db = {
            'doc_1': Chunk(
                chunk_id='doc_1',
                content='[Điều dieu_1 - Luật Đất Đai] Đất đai thuộc sở hữu toàn dân do Nhà nước đại diện chủ sở hữu. Tổ chức, cá nhân được giao quyền sử dụng.',
                parent_id='doc_1',
                chunk_type='DIEU',
                metadata={'dieu_so': 'dieu_1', 'ten_van_ban': 'Luật Đất Đai', 'so_hieu': '31/2024/QH15', 'trang_thai': 'effective'}
            ),
            'doc_old': Chunk(
                chunk_id='doc_old',
                content='[Điều dieu_2 - Luật Đất Đai Cũ] Luật cũ năm 1993 quy định người dân được cấp phát đất.',
                parent_id='doc_old',
                chunk_type='DIEU',
                metadata={'dieu_so': 'dieu_2', 'ten_van_ban': 'Luật Đất Đai Cũ', 'so_hieu': '1993/QH', 'trang_thai': 'hết_hiệu_lực'}
            )
        }
        return [mock_db[cid] for cid in chunk_ids if cid in mock_db]

def main():
    print("="*60)
    print("DEMO END-TO-END QUERY PIPELINE (CHAPTER 3)")
    print("="*60)
    
    # 1. Khởi tạo Dependencies
    normalizer = QueryNormalizer()
    rewriter = RuleBasedQueryRewriter()
    planner = RuleBasedPlanner()
    expander = LLMQueryExpander()
    retriever = MockHybridRetriever()
    reranker = MockReranker()
    
    window_manager = ContextWindowManager(max_tokens=settings.LLM_MAX_CONTEXT_TOKENS)
    context_builder = RetrievalContextBuilder(window_manager)
    prompt_builder = PromptBuilder()
    
    generator = MockLLMGenerator()
    router = LLMRouter(default_generator=generator)
    
    verifiers = [
        MockGroundednessVerifier(), 
        CitationVerifier(), 
        HallucinationDetectionVerifier(), 
        ConfidenceScoringVerifier(RuleBasedScoringStrategy())
    ]
    verification_pipeline = VerificationPipeline(verifiers)
    
    # 2. Khởi tạo Orchestrator & Façade
    orchestrator = QueryOrchestrator(
        normalizer=normalizer,
        rewriter=rewriter,
        planner=planner,
        expander=expander,
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        router=router,
        verification_pipeline=verification_pipeline
    )
    
    pipeline = QueryPipeline(orchestrator)
    
    # 3. Kịch bản Demo
    scenarios = [
        ("Đúng phạm vi (In-scope)", "Sở hữu đất đai thuộc về ai?"),
        ("Ngoài phạm vi (Out-of-scope)", "Công ty TNHH có mấy thành viên?"),
        ("Mơ hồ (Ambiguous)", "Thuộc về ai?"),
        ("Hỏi vào văn bản hết hiệu lực", "Luật cũ năm 1993 thế nào?"),
        ("Cố tình tạo ảo giác", "Tạo ra ảo giác đi")
    ]
    
    for name, query in scenarios:
        print(f"\n--- Kịch bản: {name} ---")
        print(f"User Query: {query}")
        result = pipeline.ask(query)
        
        print(f"Normalized Query: {result.normalized_query}")
        print(f"Answer: {result.answer}")
        
        if result.citations:
            print("Citations:")
            for cite in result.citations:
                print(f" - {cite.format_citation()}")
                
        print(f"Grounded: {result.is_grounded} (Score: {result.confidence_score})")
        if result.warnings:
            print("Warnings:")
            for w in result.warnings:
                 print(f" - [!] {w}")
                 
        print(f"Timing (ms): Generation={result.timing.get('generation_ms', 0):.2f}, Total Verify={result.timing.get('verification_ms', 0):.2f}")

if __name__ == "__main__":
    main()

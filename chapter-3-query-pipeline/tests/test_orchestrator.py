import pytest
from typing import List
from shared.models.schemas import Chunk
from shared.interfaces import RetrieverInterface
from module3.orchestrator import QueryOrchestrator, QueryPipeline
from module3.query_understanding import QueryNormalizer, RuleBasedQueryRewriter
from module3.reranker import MockReranker
from module3.prompt_builder import RetrievalContextBuilder, PromptBuilder, ContextWindowManager
from module3.generator import MockLLMGenerator
from module3.verifier import VerificationPipeline, MockGroundednessVerifier, CitationVerifier, HallucinationDetectionVerifier, ConfidenceScoringVerifier, RuleBasedScoringStrategy
from module3.planner import RuleBasedPlanner
from module3.expansion import LLMQueryExpander
from module3.router import LLMRouter

class DummyRetriever(RetrieverInterface):
    def retrieve(self, query: str, top_k: int = 5, filters: dict = None) -> List[Chunk]:
        return [
            Chunk(
                chunk_id="1", 
                content="test content", 
                parent_id="p1", 
                chunk_type="DIEU", 
                metadata={"trang_thai": "effective", "dieu_so": "Điều 1"}
            )
        ]
        
        
    def fetch_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        return [
            Chunk(
                chunk_id=cid,
                content=f"parent content for {cid}",
                parent_id=cid,
                chunk_type="DIEU",
                metadata={"trang_thai": "effective", "dieu_so": "Điều 1"}
            ) for cid in chunk_ids
        ]
@pytest.fixture
def orchestrator():
    normalizer = QueryNormalizer()
    rewriter = RuleBasedQueryRewriter()
    retriever = DummyRetriever()
    reranker = MockReranker()
    window_manager = ContextWindowManager(max_tokens=4000)
    context_builder = RetrievalContextBuilder(window_manager=window_manager)
    prompt_builder = PromptBuilder()
    generator = MockLLMGenerator()
    verifiers = [
        MockGroundednessVerifier(), 
        CitationVerifier(), 
        HallucinationDetectionVerifier(), 
        ConfidenceScoringVerifier(RuleBasedScoringStrategy())
    ]
    verifier = VerificationPipeline(verifiers=verifiers)
    
    planner = RuleBasedPlanner()
    expander = LLMQueryExpander()
    router = LLMRouter(default_generator=generator)
    
    return QueryOrchestrator(
        normalizer=normalizer,
        rewriter=rewriter,
        planner=planner,
        expander=expander,
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        router=router,
        verification_pipeline=verifier
    )

def test_orchestrator_run(orchestrator: QueryOrchestrator):
    query = "test query"
    result = orchestrator.run(query)
    
    # Assert result structure
    assert result.query == query
    assert result.normalized_query is not None
    assert isinstance(result.answer, str)
    assert len(result.retrieved_chunks) == 1
    assert result.retrieved_chunks[0].chunk_id == "p1"
    
    # Assert timing
    assert "retrieval_ms" in result.timing
    assert "generation_ms" in result.timing

def test_query_pipeline(orchestrator: QueryOrchestrator):
    pipeline = QueryPipeline(orchestrator=orchestrator)
    result = pipeline.ask("test query pipeline")
    assert result.query == "test query pipeline"

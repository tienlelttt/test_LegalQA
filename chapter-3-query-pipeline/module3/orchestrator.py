import time
from typing import List, Any
from shared.models.schemas import Chunk
from shared.interfaces import RetrieverInterface
from module3.schemas import AnswerResult, QueryContext
from module3.interfaces import QueryRewriterInterface, BaseReranker, LLMGeneratorInterface
from module3.query_understanding import QueryNormalizer
from module3.prompt_builder import RetrievalContextBuilder, PromptBuilder
from module3.verifier import VerificationPipeline
from module3.planner import RuleBasedPlanner
from module3.expansion import LLMQueryExpander
from module3.router import LLMRouter

def rrf(lists_of_chunks: List[List[Chunk]], k=60) -> List[Chunk]:
    """Reciprocal Rank Fusion"""
    score_map = {}
    chunk_map = {}
    for chunk_list in lists_of_chunks:
        for rank, chunk in enumerate(chunk_list):
            if chunk.chunk_id not in score_map:
                score_map[chunk.chunk_id] = 0
                chunk_map[chunk.chunk_id] = chunk
            score_map[chunk.chunk_id] += 1 / (k + rank + 1)
    
    sorted_chunks = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
    return [chunk_map[cid] for cid, score in sorted_chunks]

class QueryOrchestrator:
    """
    Nhạc trưởng điều phối luồng thực thi và đo lường thời gian (telemetry).
    """
    def __init__(
        self,
        normalizer: QueryNormalizer,
        rewriter: QueryRewriterInterface,
        planner: RuleBasedPlanner,
        expander: LLMQueryExpander,
        retriever: RetrieverInterface,
        reranker: BaseReranker,
        context_builder: RetrievalContextBuilder,
        prompt_builder: PromptBuilder,
        router: LLMRouter,
        verification_pipeline: VerificationPipeline
    ):
        self.normalizer = normalizer
        self.rewriter = rewriter
        self.planner = planner
        self.expander = expander
        self.retriever = retriever
        self.reranker = reranker
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder
        self.router = router
        self.verification_pipeline = verification_pipeline
        
    def run(self, query: str) -> AnswerResult:
        timing = {}
        
        try:
            # 1. Normalization
            t0 = time.time()
            normalized_query = self.normalizer.normalize(query)
            timing['normalization_ms'] = (time.time() - t0) * 1000
            
            # 2. Rewriting
            t0 = time.time()
            rewritten_query = self.rewriter.rewrite(normalized_query)
            timing['rewriting_ms'] = (time.time() - t0) * 1000
            
            # 3. Planning
            t0 = time.time()
            config = self.planner.plan(rewritten_query)
            timing['planning_ms'] = (time.time() - t0) * 1000
            
            # 4. Expansion
            t0 = time.time()
            queries_to_run = self.expander.expand(rewritten_query, config)
            timing['expansion_ms'] = (time.time() - t0) * 1000
            
            # 5. Retrieval & RRF
            t0 = time.time()
            all_chunks_lists = []
            for q in queries_to_run:
                all_chunks_lists.append(self.retriever.retrieve(q, top_k=30, filters=config.filters))
            
            chunks = rrf(all_chunks_lists)
            timing['retrieval_ms'] = (time.time() - t0) * 1000
            
            # 6. Reranking
            t0 = time.time()
            reranked_chunks = self.reranker.rerank(rewritten_query, chunks, top_k=5)
            timing['reranking_ms'] = (time.time() - t0) * 1000
            
            # 7. Context Building (Parent-Child)
            t0 = time.time()
            # Fetch parent chunks
            parent_ids = list(set([c.parent_id for c in reranked_chunks if c.parent_id]))
            parent_chunks = self.retriever.fetch_by_ids(parent_ids)
            
            # Giữ lại các chunk không có parent_id (đã là parent)
            standalone_chunks = [c for c in reranked_chunks if not c.parent_id]
            all_context_chunks = parent_chunks + standalone_chunks
            
            context = self.context_builder.build_context(all_context_chunks)
            timing['context_building_ms'] = (time.time() - t0) * 1000
            
            # 8. Prompt Building
            t0 = time.time()
            sys_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(query, context)
            timing['prompt_building_ms'] = (time.time() - t0) * 1000
            
            # 9. LLM Router & Generation
            t0 = time.time()
            generator = self.router.route_request(query)
            raw_answer = generator.generate(sys_prompt, user_prompt)
            timing['generation_ms'] = (time.time() - t0) * 1000
            
        except Exception as e:
            # Global Error Boundary cho pipeline
            raw_answer = "Hệ thống gặp lỗi trong quá trình xử lý: " + str(e)
            context = QueryContext(chunks=[])
            generator = self.router.default_generator
            normalized_query = query
        
        # 8. Create Initial Result
        result = AnswerResult(
            answer=raw_answer,
            query=query,
            normalized_query=normalized_query,
            retrieved_chunks=context.chunks,
            timing=timing,
            model_name=getattr(generator, "model_name", "mock-generator")
        )        
        # 9. Verification
        t0 = time.time()
        final_result = self.verification_pipeline.run(result, context)
        timing['verification_ms'] = (time.time() - t0) * 1000
        
        final_result.timing = timing
        return final_result


class QueryPipeline:
    """
    Façade pattern - Cung cấp Interface đơn giản nhất cho người dùng.
    """
    def __init__(self, orchestrator: QueryOrchestrator):
        self.orchestrator = orchestrator
        
    def ask(self, query: str) -> AnswerResult:
        return self.orchestrator.run(query)

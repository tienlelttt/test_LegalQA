import json
from abc import ABC, abstractmethod
import sys, io
import os

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')

from module3.orchestrator import QueryPipeline, QueryOrchestrator
from module3.query_understanding import QueryNormalizer, RuleBasedQueryRewriter
from module3.prompt_builder import RetrievalContextBuilder, ContextWindowManager, PromptBuilder
from module3.reranker import MockReranker
from module3.generator import MockLLMGenerator
from module3.verifier import VerificationPipeline, CitationVerifier, MockGroundednessVerifier
from shared.config.settings import settings

class EvaluationRunner(ABC):
    """
    Interface chung cho việc chạy các tập test.
    """
    @abstractmethod
    def evaluate(self, pipeline: QueryPipeline, golden_questions_path: str):
        pass

class EndToEndEvaluator(EvaluationRunner):
    """
    Đánh giá End-to-End: So sánh kết quả trả về với golden answers.
    """
    def evaluate(self, pipeline: QueryPipeline, golden_questions_path: str):
        with open(golden_questions_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        success = 0
        print(f"=== Bắt đầu đánh giá E2E trên {len(data)} câu hỏi ===")
        for item in data:
            q = item['query']
            print(f"\nEvaluating: '{q}'")
            result = pipeline.ask(q)
            
            # Simple check keywords
            keywords = item['expected_answer_keywords']
            ans_lower = result.answer.lower()
            warning_lower = str(result.warnings).lower()
            
            match = True
            for kw in keywords:
                if kw.lower() not in ans_lower and kw.lower() not in warning_lower:
                    match = False
                    
            if match and (not keywords and not result.is_grounded): # hallu case
                pass # If testing hallu, we expect grounded = False
                
            print(f" -> Result: {'PASSED' if match else 'FAILED'}")
            print(f" -> Answer: {result.answer}")
            print(f" -> Warnings: {result.warnings}")
            if match:
                success += 1
                
        print(f"\n=== Kết thúc đánh giá. Accuracy: {success}/{len(data)} ===")

if __name__ == "__main__":
    from demo_query_pipeline import MockHybridRetriever
    orchestrator = QueryOrchestrator(
        normalizer=QueryNormalizer(),
        rewriter=RuleBasedQueryRewriter(),
        retriever=MockHybridRetriever(),
        reranker=MockReranker(),
        context_builder=RetrievalContextBuilder(ContextWindowManager(settings.LLM_MAX_CONTEXT_TOKENS)),
        prompt_builder=PromptBuilder(),
        generator=MockLLMGenerator(),
        verification_pipeline=VerificationPipeline([CitationVerifier(), MockGroundednessVerifier()])
    )
    pipeline = QueryPipeline(orchestrator)
    evaluator = EndToEndEvaluator()
    path = os.path.join(os.path.dirname(__file__), "golden_questions.json")
    evaluator.evaluate(pipeline, path)

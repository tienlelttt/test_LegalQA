from typing import Sequence, List
import re
from abc import ABC, abstractmethod
from module3.interfaces import BaseVerifier
from module3.schemas import AnswerResult, QueryContext, Citation

class CitationVerifier(BaseVerifier):
    """
    [12] Kiểm tra Citation: Citation mismatch và Missing citation.
    """
    def verify(self, answer_result: AnswerResult, context: QueryContext) -> AnswerResult:
        if "không tìm đủ căn cứ" in answer_result.answer.lower():
            return answer_result

        pattern = r"\[Điều (.*?) — (.*?), (.*?)\]"
        citations_found = re.findall(r"\[(Điều .*?)\]", answer_result.answer)
        
        if not citations_found:
            answer_result.warnings.append("Missing citation: Câu trả lời không chứa trích dẫn đúng chuẩn.")
            return answer_result
            
        for cite_text in citations_found:
            try:
                dieu_part = cite_text.split("—")[0].strip()
                vanban_part = cite_text.split("—")[1].strip() if "—" in cite_text else ""
                
                cite = Citation(
                    chunk_id="unknown",
                    dieu_so=dieu_part,
                    ten_van_ban=vanban_part.split(",")[0].strip() if "," in vanban_part else vanban_part,
                    so_hieu=vanban_part.split(",")[1].strip() if "," in vanban_part else ""
                )
                answer_result.citations.append(cite)
            except Exception:
                pass
                
        valid = False
        for chunk in context.chunks:
            chunk_dieu = chunk.metadata.get("dieu_so", "")
            for cite in answer_result.citations:
                if chunk_dieu and chunk_dieu in cite.dieu_so:
                    valid = True
                    break
        
        if not valid:
             answer_result.warnings.append("Citation mismatch: Nguồn trích dẫn không khớp với văn bản truy xuất.")
             
        return answer_result

class MockGroundednessVerifier(BaseVerifier):
    """
    [11] Simulation Layer cho Groundedness Check.
    Kiểm tra câu trả lời có bịa đặt hoặc tự suy diễn so với context không.
    """
    def verify(self, answer_result: AnswerResult, context: QueryContext) -> AnswerResult:
        if "ảo giác" in answer_result.answer.lower() or "tuyệt đối" in answer_result.answer.lower():
            answer_result.warnings.append("Unsupported claim: Câu trả lời có dấu hiệu tự suy diễn.")
            answer_result.is_grounded = False
        else:
            answer_result.is_grounded = True
            
        return answer_result

class HallucinationDetectionVerifier(BaseVerifier):
    """
    [13] Hallucination Detection.
    Tổng hợp nhãn từ [11] Groundedness và [12] Citation thành một mức rủi ro duy nhất (thấp/trung bình/cao).
    """
    def verify(self, answer_result: AnswerResult, context: QueryContext) -> AnswerResult:
        has_groundedness_warning = any("Unsupported claim" in w for w in answer_result.warnings) or not answer_result.is_grounded
        has_citation_warning = any("Citation mismatch" in w or "Missing citation" in w for w in answer_result.warnings)
        
        if has_groundedness_warning and has_citation_warning:
            answer_result.hallucination_risk = "high"
        elif has_groundedness_warning or has_citation_warning:
            answer_result.hallucination_risk = "medium"
        else:
            answer_result.hallucination_risk = "low"
            
        # Nếu rủi ro cao, có thể quyết định từ chối trả lời (override answer)
        if answer_result.hallucination_risk == "high" and "không tìm đủ căn cứ" not in answer_result.answer.lower():
            answer_result.answer = "Hệ thống không tìm đủ căn cứ rõ ràng để trả lời chính xác câu hỏi này (Rủi ro ảo giác cao)."
            
        return answer_result

class ScoringStrategy(ABC):
    @abstractmethod
    def calculate_score(self, answer_result: AnswerResult, context: QueryContext) -> float:
        pass

class RuleBasedScoringStrategy(ScoringStrategy):
    """Chiến lược tính điểm dựa trên luật/heuristic"""
    def calculate_score(self, answer_result: AnswerResult, context: QueryContext) -> float:
        if answer_result.hallucination_risk == "high":
            return 0.1
        elif answer_result.hallucination_risk == "medium":
            return 0.5
        elif answer_result.hallucination_risk == "low":
            return 0.95
        return 0.0

class ConfidenceScoringVerifier(BaseVerifier):
    """
    [14] Confidence Scoring.
    Cho người dùng biết mức độ tin cậy của câu trả lời.
    Sử dụng Strategy pattern để có thể thay đổi thuật toán tính điểm linh hoạt.
    """
    def __init__(self, strategy: ScoringStrategy):
        self.strategy = strategy
        
    def verify(self, answer_result: AnswerResult, context: QueryContext) -> AnswerResult:
        answer_result.confidence_score = self.strategy.calculate_score(answer_result, context)
        return answer_result

class NLIGroundednessVerifier(BaseVerifier):
    """
    Production Layer cho Groundedness.
    Sử dụng mô hình NLI (Natural Language Inference) như DeBERTa-v3-large-mnli
    """
    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-large"):
        self.model_name = model_name
        self.model = None
        
    def verify(self, answer_result: AnswerResult, context: QueryContext) -> AnswerResult:
        if not self.model:
            return answer_result
        raise NotImplementedError("Cần cài đặt sentence-transformers và cấu hình NLI model.")

class VerificationPipeline:
    """
    Chuỗi các verifier để chạy tuần tự.
    """
    def __init__(self, verifiers: Sequence[BaseVerifier]):
        self.verifiers = verifiers
        
    def run(self, answer_result: AnswerResult, context: QueryContext) -> AnswerResult:
        for verifier in self.verifiers:
            answer_result = verifier.verify(answer_result, context)
            
        return answer_result

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from shared.models.schemas import Chunk
from module3.schemas import AnswerResult, QueryContext

class QueryRewriterInterface(ABC):
    """
    Interface cho các Query Rewriter.
    Mục tiêu: Viết lại câu hỏi để truy xuất (retrieval) tốt hơn.
    """
    @abstractmethod
    def rewrite(self, query: str) -> str:
        pass

class BaseReranker(ABC):
    """
    Interface cho các Reranker.
    Mục tiêu: Đánh giá lại độ liên quan thực sự của các chunk đối với query.
    """
    @abstractmethod
    def rerank(self, query: str, chunks: List[Chunk], top_k: int) -> List[Chunk]:
        pass

class LLMGeneratorInterface(ABC):
    """
    Interface cho bộ sinh văn bản (LLM Generator).
    Mục tiêu: Sinh ra câu trả lời dựa trên context và query, đảm bảo format dễ parse.
    """
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        pass

class BaseVerifier(ABC):
    """
    Interface cho các Verifier trong Verification Pipeline.
    Mục tiêu: Kiểm tra câu trả lời sinh ra có đảm bảo tính xác thực không.
    """
    @abstractmethod
    def verify(self, answer_result: AnswerResult, context: QueryContext) -> AnswerResult:
        """
        Nhận vào AnswerResult và context, cập nhật các trường như is_grounded, warnings...
        rồi trả về AnswerResult đã được đánh giá.
        """
        pass

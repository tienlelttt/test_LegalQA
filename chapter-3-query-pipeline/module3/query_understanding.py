import re
import unicodedata
from module3.interfaces import QueryRewriterInterface

class QueryNormalizer:
    """
    Chuẩn hóa câu hỏi đầu vào: Unicode, khoảng trắng, viết tắt cơ bản.
    """
    def normalize(self, query: str) -> str:
        if not query:
            return ""
        
        # Chuẩn hóa Unicode (NFC để đảm bảo tiếng Việt chuẩn)
        query = unicodedata.normalize("NFC", query)
        
        # Xóa khoảng trắng thừa
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Mở rộng một số từ viết tắt phổ biến (Tùy chọn)
        query = query.replace(" NĐ ", " Nghị định ")
        query = query.replace(" TT ", " Thông tư ")
        query = query.replace(" LĐ ", " Luật đất đai ")
        
        return query

class RuleBasedQueryRewriter(QueryRewriterInterface):
    """
    Query Rewriter dùng Rule (Simulation Layer).
    Bóc tách các intent cơ bản bằng Regex.
    """
    def rewrite(self, query: str) -> str:
        # Trong thực tế, có thể biến đổi các từ như "cho tôi hỏi", "quy định ở đâu" 
        # thành các keyword súc tích hơn.
        stop_words = ["cho tôi hỏi", "làm ơn", "vui lòng", "bạn ơi", "quy định ở đâu", "cho biết"]
        rewritten = query.lower()
        for word in stop_words:
            rewritten = rewritten.replace(word, "")
        
        return re.sub(r'\s+', ' ', rewritten).strip()

class MockQueryRewriter(QueryRewriterInterface):
    """
    Query Rewriter Mock: Dành cho Unit test.
    """
    def rewrite(self, query: str) -> str:
        return query + " (rewritten)"

class LLMQueryRewriter(QueryRewriterInterface):
    """
    Query Rewriter bằng LLM (Production Layer).
    Tương lai sẽ gọi API LLM để viết lại query (ví dụ: giải quyết co-reference, thêm context hội thoại).
    """
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        
    def rewrite(self, query: str) -> str:
        # TODO: Cắm API gọi LLM ở đây. Hiện tại trả về nguyên gốc để tránh lỗi.
        return query

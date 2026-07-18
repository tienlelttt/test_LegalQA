from module3.interfaces import LLMGeneratorInterface

class LLMRouter:
    """
    Quyết định chọn model LLM tuỳ thuộc vào độ phức tạp của câu hỏi.
    """
    def __init__(self, default_generator: LLMGeneratorInterface, fallback_generator: LLMGeneratorInterface = None):
        self.default_generator = default_generator
        self.fallback_generator = fallback_generator if fallback_generator else default_generator
        
    def route_request(self, query: str) -> LLMGeneratorInterface:
        query_lower = query.lower()
        if "so sánh" in query_lower or "phân tích" in query_lower or "tổng hợp" in query_lower:
            # Dùng model lớn/tốt hơn cho câu hỏi phức tạp
            return self.fallback_generator
        # Dùng model mặc định (ví dụ Qwen-3B) cho câu hỏi đơn giản
        return self.default_generator

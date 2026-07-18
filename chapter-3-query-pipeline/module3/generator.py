from module3.interfaces import LLMGeneratorInterface
import re

class MockLLMGenerator(LLMGeneratorInterface):
    """
    Giả lập LLM Generator. Dành cho Unit test và demo khi chưa có API.
    Sử dụng Regex đơn giản để tìm ra "câu trả lời" từ context.
    """
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # Nếu câu hỏi nói về "sở hữu", "thuộc về ai", ta hardcode trả lời từ context
        query_part = user_prompt.split("CÂU HỎI:\n")[-1].lower()
        context_part = user_prompt.split("NGỮ CẢNH (CONTEXT):")[1].split("CÂU HỎI:")[0]
        
        if "sở hữu" in query_part or "thuộc về ai" in query_part:
            if "Nguồn 1 - Điều dieu_1 - Luật Đất Đai" in context_part:
                 return "Đất đai thuộc sở hữu toàn dân do Nhà nước đại diện chủ sở hữu. [Điều dieu_1, Khoản None — Luật Đất Đai, 31/2024/QH15]"
                 
        if "hết hiệu lực" in query_part:
            return "Hệ thống không tìm đủ căn cứ để trả lời."
            
        if "ảo giác" in query_part:
            # Cố tình sinh ảo giác
            return "Người dùng sở hữu đất đai tuyệt đối. [Điều dieu_1, Khoản None — Luật Đất Đai, 31/2024/QH15]"
            
        # Fallback chung
        if "Nguồn 1" not in context_part:
            return "Hệ thống không tìm đủ căn cứ để trả lời."
            
        return f"Dựa vào thông tin cung cấp, tôi có thể trả lời câu hỏi của bạn. [Điều dieu_2, Khoản None — Luật Đất Đai, 31/2024/QH15]"

class ProductionLLMGenerator(LLMGeneratorInterface):
    """
    LLM Generator thực tế (gọi qua OpenAI / vLLM / Gemini).
    """
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model_name = model_name
        
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # TODO: Implement API call
        raise NotImplementedError("ProductionLLMGenerator chưa được triển khai.")

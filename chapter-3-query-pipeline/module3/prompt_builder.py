from typing import List, Tuple
from shared.models.schemas import Chunk
from module3.schemas import QueryContext

class ContextWindowManager:
    """
    Quản lý token (dựa trên từ hoặc subword) cho context window của LLM.
    Đảm bảo tổng dung lượng context không vượt quá giới hạn.
    """
    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        
    def estimate_tokens(self, text: str) -> int:
        """Ước tính token. Đơn giản hóa: 1 từ ~ 1.3 token tiếng Việt."""
        return int(len(text.split()) * 1.3)

    def prune_chunks(self, chunks: List[Chunk]) -> Tuple[List[Chunk], int, bool]:
        """
        Cắt tỉa danh sách chunks để nhét vừa vào context window.
        Giữ lại các chunk ở trên cùng (do đã được rerank).
        """
        pruned = []
        current_tokens = 0
        is_pruned = False
        
        for chunk in chunks:
            chunk_tokens = self.estimate_tokens(chunk.content)
            if current_tokens + chunk_tokens > self.max_tokens:
                is_pruned = True
                break
            pruned.append(chunk)
            current_tokens += chunk_tokens
            
        return pruned, current_tokens, is_pruned


class RetrievalContextBuilder:
    """
    Gộp và xử lý danh sách chunks trước khi đưa vào Prompt.
    """
    def __init__(self, window_manager: ContextWindowManager):
        self.window_manager = window_manager
        
    def build_context(self, chunks: List[Chunk]) -> QueryContext:
        """
        Lọc, nối và cắt tỉa (prune) các chunks.
        """
        pruned_chunks, tokens, is_pruned = self.window_manager.prune_chunks(chunks)
        return QueryContext(
            chunks=pruned_chunks,
            total_tokens=tokens,
            is_pruned=is_pruned
        )


class PromptBuilder:
    """
    Tách biệt System Prompt, User Prompt, và định dạng Context.
    """
    def build_system_prompt(self) -> str:
        return (
            "Bạn là trợ lý pháp lý AI chuyên nghiệp về pháp luật Việt Nam.\n"
            "Mục tiêu của bạn là trả lời câu hỏi DỰA TRÊN NGỮ CẢNH CUNG CẤP.\n"
            "TUYỆT ĐỐI tuân thủ các quy tắc sau:\n"
            "1. KHÔNG tự bịa ra thông tin. Nếu ngữ cảnh không có thông tin, hãy trả lời 'Hệ thống không tìm đủ căn cứ để trả lời'.\n"
            "2. BẮT BUỘC trích dẫn nguồn cho mỗi câu khẳng định, định dạng: [Điều X, Khoản Y — Tên văn bản, số hiệu].\n"
            "3. Ngôn từ trang trọng, khách quan.\n\n"
            "=== VÍ DỤ MINH HỌA (FEW-SHOT EXAMPLES) ===\n"
            "Q: Đất đai thuộc sở hữu của ai?\n"
            "A: Đất đai thuộc sở hữu toàn dân do Nhà nước đại diện chủ sở hữu. [Điều 1 — Luật Đất Đai, 31/2024/QH15]\n"
            "Q: Tốc độ tối đa trong khu đông dân cư là bao nhiêu?\n"
            "A: Hệ thống không tìm đủ căn cứ để trả lời.\n\n"
            "=== OUTPUT FORMAT ===\n"
            "Trả về câu trả lời trực tiếp, kèm theo trích dẫn chuẩn xác.\n"
        )
        
    def format_context(self, context: QueryContext) -> str:
        formatted = ""
        for i, chunk in enumerate(context.chunks):
            # Tạo nhãn nguồn để LLM có thể dễ dàng trích dẫn
            dieu_so = chunk.metadata.get('dieu_so', '')
            ten_van_ban = chunk.metadata.get('ten_van_ban', '')
            khoan_so = chunk.metadata.get('khoan_so', '')
            
            source_label = f"Nguồn {i+1} - Điều {dieu_so} - {ten_van_ban}"
            if khoan_so:
                 source_label += f" Khoản {khoan_so}"
            
            formatted += f"[{source_label}]\n{chunk.content}\n\n"
        return formatted
        
    def build_user_prompt(self, query: str, context: QueryContext) -> str:
        context_str = self.format_context(context)
        return (
            f"NGỮ CẢNH (CONTEXT):\n"
            f"-------------------\n"
            f"{context_str}\n"
            f"-------------------\n\n"
            f"CÂU HỎI:\n{query}"
        )

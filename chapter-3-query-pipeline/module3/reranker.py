from typing import List
import random
from shared.models.schemas import Chunk
from module3.interfaces import BaseReranker

class MockReranker(BaseReranker):
    """
    Reranker dùng để mô phỏng (Mock), xáo trộn nhẹ điểm và loại bỏ văn bản hết hiệu lực.
    """
    def rerank(self, query: str, chunks: List[Chunk], top_k: int) -> List[Chunk]:
        # Xáo trộn nhẹ để giả lập thay đổi thứ hạng
        random.shuffle(chunks) 
        
        return chunks[:top_k]


class RuleBasedReranker(BaseReranker):
    """
    Reranker dựa trên Keyword overlap (Jaccard).
    """
    def rerank(self, query: str, chunks: List[Chunk], top_k: int) -> List[Chunk]:
        query_words = set(query.lower().split())
        
        def score(chunk: Chunk):
            # Điểm từ vựng
            chunk_words = set(chunk.content.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            
            # Boost nếu có match tiêu đề/Điều
            boost = 0
            dieu_so = chunk.metadata.get("dieu_so", "")
            if dieu_so and dieu_so in query:
                boost += 5
            
            # Phạt nếu hết hiệu lực
            penalty = -100 if chunk.metadata.get("trang_thai", "") == "hết_hiệu_lực" else 0
            
            return overlap + boost + penalty

        ranked = sorted(chunks, key=score, reverse=True)
        # Chỉ lấy những chunk có điểm > 0
        filtered = [c for c in ranked if score(c) >= 0]
        
        return filtered[:top_k]


class CrossEncoderReranker(BaseReranker):
    """
    Reranker sử dụng mô hình CrossEncoder (như BGE-reranker hoặc mMarco).
    Đây là Production Layer hoặc Local Simulation cho Reranker.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        try:
            from sentence_transformers import CrossEncoder
            # Chạy trên CPU, tải model lần đầu sẽ mất chút thời gian
            self.model = CrossEncoder(model_name, max_length=512)
        except ImportError:
            self.model = None
            print("WARNING: Cần cài đặt `sentence-transformers` để chạy CrossEncoderReranker.")
            
    def rerank(self, query: str, chunks: List[Chunk], top_k: int) -> List[Chunk]:
        if not chunks:
            return []
            
        if not self.model:
            print("CrossEncoder chưa sẵn sàng, trả về danh sách nguyên gốc.")
            return chunks[:top_k]
            
        # Chuẩn bị cặp (Query, Chunk text)
        pairs = [[query, c.content] for c in chunks]
        
        # Chấm điểm neural
        neural_scores = self.model.predict(pairs)
        
        # Áp dụng Rule-based boost
        final_scores = []
        for i, chunk in enumerate(chunks):
            score = neural_scores[i]
            # Boost nếu metadata chứa thông tin uy tín
            if chunk.metadata.get("trang_thai") == "effective":
                score += 0.5  # Boost nhẹ
            if chunk.metadata.get("ten_van_ban", "") in query:
                score += 1.0  # Boost mạnh
            final_scores.append(score)
        
        scored_chunks = [(chunk, score) for chunk, score in zip(chunks, final_scores)]
            
        ranked = sorted(scored_chunks, key=lambda x: x[1], reverse=True)
        return [chunk for chunk, score in ranked][:top_k]

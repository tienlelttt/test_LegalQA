import pytest
import sys
import os
chapter_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if chapter_dir not in sys.path:
    sys.path.insert(0, chapter_dir)

from src.chunker import AdaptiveChunker
from shared.models.schemas import LegalDocument, Chuong, Dieu, Khoan, Diem, Metadata

def test_hierarchical_semantic_chunker():
    doc = LegalDocument(metadata=Metadata(document_id="123/2024/QH15"))
    chuong = Chuong(id="chuong_1", title="Chương I")
    
    # Điều 1: Dưới giới hạn -> Không bị chẻ (1 chunk)
    dieu1 = Dieu(id="dieu_1", title="Điều 1", content="Nội dung rất ngắn.")
    khoan1_d1 = Khoan(id="dieu_1_khoan_1", content="1. Khoản 1")
    dieu1.khoan_list = [khoan1_d1]
    
    # Điều 2: Vượt giới hạn -> Bị chẻ xuống cấp Khoản
    dieu2 = Dieu(id="dieu_2", title="Điều 2", content="")
    khoan1_d2 = Khoan(id="dieu_2_khoan_1", content="1. Khoản 1 dài: " + "a "*50)
    khoan2_d2 = Khoan(id="dieu_2_khoan_2", content="2. Khoản 2 dài: " + "b "*50)
    dieu2.khoan_list = [khoan1_d2, khoan2_d2]
    
    chuong.dieu_list = [dieu1, dieu2]
    doc.chuong_list = [chuong]
    
    # Set max_words rất thấp (vd: 60 từ) để kích hoạt tách Điều 2
    chunker = AdaptiveChunker(max_words=60)
    chunks = chunker.chunk(doc)
    
    # Chunk 1: Điều 1 (Vì 5 từ < 20 từ) -> type DIEU
    assert chunks[0].chunk_type == "DIEU"
    assert chunks[0].chunk_id == "dieu_1"
    
    # Chunk 2, 3: Khoản 1, Khoản 2 của Điều 2 (Vì text Điều 2 > 20 từ) -> type KHOAN
    assert chunks[1].chunk_type == "KHOAN"
    assert chunks[1].chunk_id == "dieu_2_khoan_1"
    assert chunks[2].chunk_type == "KHOAN"
    assert chunks[2].chunk_id == "dieu_2_khoan_2"
    
    # Kiểm tra metadata truyền vào có chuẩn không
    assert chunks[1].metadata["dieu_id"] == "dieu_2"
    assert chunks[1].metadata["prev_dieu_id"] == "dieu_1"
    
def test_sliding_window_fallback():
    doc = LegalDocument(metadata=Metadata(document_id="123/2024/QH15"))
    chuong = Chuong(id="chuong_1", title="Chương I")
    
    # Điều 1 siêu dài nhưng KHÔNG CÓ khoản -> Bắt buộc dùng sliding window
    dieu1 = Dieu(id="dieu_1", title="Điều 1", content="Từ "*100)
    chuong.dieu_list = [dieu1]
    doc.chuong_list = [chuong]
    
    chunker = AdaptiveChunker(max_words=30)
    chunks = chunker.chunk(doc)
    
    # Nên có nhiều chunk do fallback
    assert len(chunks) > 1
    assert chunks[0].chunk_type == "DIEU_SLIDING"
    assert "window" in chunks[0].chunk_id

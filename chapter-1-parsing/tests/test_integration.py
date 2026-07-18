import pytest
import sys
import os
from src.cleaner import LegalCleaner
from src.parser import LegalStructureParser
from src.extractor import RegexMetadataExtractor, MockLLMMetadataExtractor
from src.chunker import AdaptiveChunker


from shared.paths import get_mock_file
with open(get_mock_file("luat_dat_dai.txt"), "r", encoding="utf-8") as f:
    MOCK_LUAT_DAT_DAI = f.read()

def test_full_pipeline():
    # 1. Clean
    cleaner = LegalCleaner()
    cleaned_text = cleaner.clean(MOCK_LUAT_DAT_DAI)
    
    # 2. Parse
    parser = LegalStructureParser()
    doc = parser.parse(cleaned_text)
    
    # 3. Extract Metadata
    base_extractor = RegexMetadataExtractor()
    extractor = MockLLMMetadataExtractor(base_extractor)
    doc = extractor.extract_metadata(cleaned_text, doc)
    
    # 4. Chunk
    chunker = AdaptiveChunker(max_words=200) # Giới hạn vừa phải
    chunks = chunker.chunk(doc)
    
    assert doc.metadata.document_id == "31/2024/QH15"
    assert "Khoản 2 Điều 4 của Luật Doanh nghiệp" in doc.metadata.citations
    
    # Vì max_words = 200, các Điều trong Mock đều khá ngắn (dưới 200 từ)
    # -> Sẽ chỉ tạo ra các Chunk cấp ĐIỀU
    # Mock có 3 Điều -> 3 Chunks (không bị xé lẻ)
    assert len(chunks) == 3
    assert chunks[0].chunk_type == "DIEU"
    
    # Kiểm tra metadata truyền vào chunk
    assert chunks[0].metadata["document_id"] == "31/2024/QH15"
    assert chunks[0].metadata["dieu_id"] == "dieu_1"

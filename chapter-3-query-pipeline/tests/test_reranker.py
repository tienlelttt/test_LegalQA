import pytest
from typing import List
import sys
from unittest.mock import MagicMock
from shared.models.schemas import Chunk
from module3.reranker import MockReranker, RuleBasedReranker, CrossEncoderReranker

@pytest.fixture
def sample_chunks() -> List[Chunk]:
    return [
        Chunk(chunk_id="1", content="Nội dung điều 1 về pccc", parent_id="p1", chunk_type="DIEU", metadata={"trang_thai": "effective", "dieu_so": "Điều 1"}),
        Chunk(chunk_id="2", content="Nội dung cũ", parent_id="p2", chunk_type="DIEU", metadata={"trang_thai": "hết_hiệu_lực", "dieu_so": "Điều 2"}),
        Chunk(chunk_id="3", content="Nội dung khác liên quan đến pccc", parent_id="p3", chunk_type="DIEU", metadata={"trang_thai": "effective", "dieu_so": "Điều 3"}),
    ]

def test_mock_reranker(sample_chunks: List[Chunk]):
    reranker = MockReranker()
    reranked = reranker.rerank("query pccc", sample_chunks, top_k=5)
    assert len(reranked) == 3

def test_rule_based_reranker(sample_chunks: List[Chunk]):
    reranker = RuleBasedReranker()
    query = "pccc nội dung Điều 1"
    reranked = reranker.rerank(query, sample_chunks, top_k=5)
    
    assert len(reranked) >= 1
    # chunk 1 should score highest (match 'nội dung', 'pccc' and boost from dieu_so)
    assert reranked[0].chunk_id == "1"
    # chunk 2 should have negative score and be filtered out
    assert not any(c.chunk_id == "2" for c in reranked)

def test_cross_encoder_reranker_mock(sample_chunks: List[Chunk]):
    # Mock sentence_transformers so it doesn't download models
    sys.modules['sentence_transformers'] = MagicMock()
    
    # CrossEncoderReranker without sentence-transformers will just filter and return
    reranker = CrossEncoderReranker(model_name="dummy")
    reranker.model = None # Force mock
    
    reranked = reranker.rerank("query", sample_chunks, top_k=5)
    assert len(reranked) == 3
    
    # Clean up mock
    del sys.modules['sentence_transformers']

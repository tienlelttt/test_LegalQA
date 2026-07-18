import pytest
from shared.models.schemas import Chunk
from module3.prompt_builder import RetrievalContextBuilder, PromptBuilder, ContextWindowManager

from typing import List

@pytest.fixture
def sample_chunks() -> List[Chunk]:
    return [
        Chunk(chunk_id="1", content="Nội dung điều 1 về pccc", parent_id="p1", chunk_type="DIEU", metadata={"trang_thai": "effective", "dieu_so": "Điều 1", "so_hieu": "11/2024", "ten_van_ban": "Luật ABC"}),
        Chunk(chunk_id="2", content="Nội dung khoản 2", parent_id="p1", chunk_type="KHOAN", metadata={"trang_thai": "effective", "khoan_so": "Khoản 2", "so_hieu": "11/2024", "ten_van_ban": "Luật ABC"}),
    ]

def test_context_builder(sample_chunks: List[Chunk]):
    window_manager = ContextWindowManager(max_tokens=4000)
    builder = RetrievalContextBuilder(window_manager=window_manager)
    context = builder.build_context(sample_chunks)
    
    # Check context contains chunks
    assert len(context.chunks) == 2
    assert context.total_tokens > 0

def test_prompt_builder(sample_chunks: List[Chunk]):
    window_manager = ContextWindowManager(max_tokens=4000)
    context_builder = RetrievalContextBuilder(window_manager=window_manager)
    context = context_builder.build_context(sample_chunks)
    
    builder = PromptBuilder()
    sys_prompt = builder.build_system_prompt()
    assert "trợ lý pháp lý" in sys_prompt.lower()
    
    query = "Hỏi về pccc?"
    user_prompt = builder.build_user_prompt(query, context)
    
    assert query in user_prompt
    assert "Điều 1" in user_prompt

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from shared.models.schemas import Chunk

class QueryConfig(BaseModel):
    filters: Dict[str, Any] = Field(default_factory=dict)
    use_hyde: bool = False
    use_graph: bool = False
    is_multi_hop: bool = False

class Citation(BaseModel):
    chunk_id: str
    dieu_so: str
    khoan_so: Optional[str] = None
    diem: Optional[str] = None
    ten_van_ban: str
    so_hieu: str
    
    def format_citation(self) -> str:
        """Định dạng citation để trả về user"""
        parts = [self.dieu_so]
        if self.khoan_so:
            parts.insert(0, f"Khoản {self.khoan_so}")
        if self.diem:
            parts.insert(0, f"Điểm {self.diem}")
        
        ref = ", ".join(parts)
        return f"[{ref} — {self.ten_van_ban}, {self.so_hieu}]"

class AnswerResult(BaseModel):
    # Dữ liệu chính
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    
    # Telemetry & Metadata (Mở rộng cho API và Monitoring)
    query: str
    normalized_query: Optional[str] = None
    confidence_score: float = 0.0
    is_grounded: bool = False
    hallucination_risk: str = "low"
    retrieved_chunks: List[Chunk] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Timings
    timing: Dict[str, float] = Field(default_factory=dict)
    
    # Model Metadata
    model_name: Optional[str] = None
    pipeline_version: str = "v3"

class QueryContext(BaseModel):
    """Context được build sau retrieval và reranking"""
    chunks: List[Chunk]
    total_tokens: int = 0
    is_pruned: bool = False

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Metadata(BaseModel):
    document_id: str = Field(default="", description="Số hiệu văn bản (vd: 31/2024/QH15)")
    title: str = Field(default="", description="Tên văn bản")
    effective_date: str = Field(default="", description="Ngày hiệu lực")
    issuing_body: str = Field(default="", description="Cơ quan ban hành")
    status: str = Field(default="effective", description="Trạng thái hiệu lực")
    citations: List[str] = Field(default_factory=list, description="Danh sách các viện dẫn Điều X Luật Y")

class Diem(BaseModel):
    id: str = Field(description="ID định danh Điểm (vd: dieu_1_khoan_1_diem_a)")
    content: str = Field(description="Nội dung Điểm")
    
class Khoan(BaseModel):
    id: str = Field(description="ID định danh Khoản")
    content: str = Field(description="Nội dung dòng đầu của Khoản")
    diem_list: List[Diem] = Field(default_factory=list)
    
class Dieu(BaseModel):
    id: str = Field(description="ID định danh Điều (vd: dieu_1)")
    title: str = Field(default="", description="Tiêu đề Điều")
    content: str = Field(description="Nội dung dòng đầu của Điều (nếu có)")
    khoan_list: List[Khoan] = Field(default_factory=list)
    
class Chuong(BaseModel):
    id: str = Field(description="ID định danh Chương")
    title: str = Field(default="", description="Tiêu đề Chương")
    dieu_list: List[Dieu] = Field(default_factory=list)

class LegalDocument(BaseModel):
    metadata: Metadata = Field(default_factory=Metadata)
    chuong_list: List[Chuong] = Field(default_factory=list)

class Chunk(BaseModel):
    chunk_id: str = Field(description="ID duy nhất của chunk")
    content: str = Field(description="Văn bản của chunk đưa vào embedding")
    parent_id: str = Field(description="ID của cấu trúc cha (Điều/Khoản chứa nó)")
    chunk_type: str = Field(description="Cấp độ ngữ nghĩa: DIEU, KHOAN, DIEM, SLIDING_WINDOW")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Payload đi kèm vào VectorDB")

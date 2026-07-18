import logging
from typing import List, Dict, Any
from shared.models.schemas import LegalDocument, Chunk, Dieu, Khoan, Diem
from shared.config.settings import settings

logger = logging.getLogger(__name__)

class AdaptiveChunker:
    """
    Hierarchical Semantic Chunker (Chương -> Điều -> Khoản -> Điểm).
    Giới hạn token chỉ là hard constraint. Ưu tiên giữ nguyên đơn vị pháp lý lớn nhất có thể.
    """
    def __init__(self, max_words: int = settings.MAX_WORDS):
        self.max_words = max_words
        
    def _count_words(self, text: str) -> int:
        # Simple word count approximation for tokens
        return len(text.split())
        
    def _get_full_dieu_text(self, dieu: Dieu) -> str:
        text = dieu.title + "\n" + dieu.content
        for k in dieu.khoan_list:
            text += "\n" + self._get_full_khoan_text(k)
        return text.strip()
        
    def _get_full_khoan_text(self, khoan: Khoan) -> str:
        text = khoan.content
        for diem in khoan.diem_list:
            text += "\n" + diem.content
        return text.strip()

    def _sliding_window_fallback(self, text: str, base_metadata: Dict[str, Any], parent_id: str, chunk_type: str) -> List[Chunk]:
        """
        Fallback cuối cùng: Nếu một đoạn (Điểm/Khoản) quá dài, cắt bằng sliding window.
        Thực tế RẤT HIẾM khi xảy ra trong văn bản luật Việt Nam.
        """
        logger.warning(f"Kích hoạt Sliding Window Fallback cho {parent_id}")
        words = text.split()
        chunks = []
        window_size = self.max_words
        overlap = int(self.max_words * 0.1) # 10% overlap
        
        start = 0
        idx = 1
        while start < len(words):
            end = min(start + window_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(Chunk(
                chunk_id=f"{parent_id}_window_{idx}",
                content=chunk_text,
                parent_id=parent_id,
                chunk_type=f"{chunk_type}_SLIDING",
                metadata=base_metadata
            ))
            start += (window_size - overlap)
            idx += 1
        return chunks

    def chunk(self, document: LegalDocument) -> List[Chunk]:
        chunks: List[Chunk] = []
        
        # Flatten để lấy thứ tự Điều
        all_dieus = []
        for chuong in document.chuong_list:
            for dieu in chuong.dieu_list:
                # Inject chuong_id into Dieu object conceptually for metadata
                dieu_dict = {"dieu": dieu, "chuong_id": chuong.id}
                all_dieus.append(dieu_dict)
            
        for i, item in enumerate(all_dieus):
            dieu = item["dieu"]
            chuong_id = item["chuong_id"]
            
            # Context window pointers
            prev_id = all_dieus[i-1]["dieu"].id if i > 0 else None
            next_id = all_dieus[i+1]["dieu"].id if i < len(all_dieus)-1 else None
            
            base_metadata = {
                "document_id": document.metadata.document_id,
                "title": document.metadata.title,
                "effective_date": document.metadata.effective_date,
                "status": document.metadata.status,
                "citations": document.metadata.citations,
                "chuong_id": chuong_id,
                "dieu_id": dieu.id,
                "prev_dieu_id": prev_id,
                "next_dieu_id": next_id
            }
            
            full_dieu_text = self._get_full_dieu_text(dieu)
            
            # [1] Xét cấp ĐIỀU
            if self._count_words(full_dieu_text) <= self.max_words or not dieu.khoan_list:
                # Nếu nguyên Điều nằm trong giới hạn, HOẶC Điều không chia Khoản (nhưng vượt giới hạn -> fallback window)
                if self._count_words(full_dieu_text) <= self.max_words:
                    chunks.append(Chunk(
                        chunk_id=dieu.id,
                        content=full_dieu_text,
                        parent_id=dieu.id,
                        chunk_type="DIEU",
                        metadata=base_metadata
                    ))
                else:
                    # Điều không có Khoản nhưng lại quá dài (rất hiếm)
                    chunks.extend(self._sliding_window_fallback(full_dieu_text, base_metadata, dieu.id, "DIEU"))
                continue
                
            # [2] Nếu cấp ĐIỀU vượt giới hạn -> Tách cấp KHOẢN
            # (Phần nội dung gốc của Điều nếu có cũng phải lưu lại)
            dieu_header = dieu.title + "\n" + dieu.content if dieu.content else dieu.title
            if dieu.content.strip():
                # Lưu header như một chunk nhỏ để không mất thông tin context
                chunks.append(Chunk(
                    chunk_id=f"{dieu.id}_header",
                    content=dieu_header,
                    parent_id=dieu.id,
                    chunk_type="DIEU_HEADER",
                    metadata=base_metadata
                ))
            
            for khoan in dieu.khoan_list:
                full_khoan_text = self._get_full_khoan_text(khoan)
                
                # Check giới hạn của Khoản
                if self._count_words(full_khoan_text) <= self.max_words or not khoan.diem_list:
                    if self._count_words(full_khoan_text) <= self.max_words:
                        # Gắn kèm title Điều vào đầu chunk Khoản để bù đắp context (RAG best practice)
                        content_with_context = f"({dieu.title}) {full_khoan_text}"
                        chunks.append(Chunk(
                            chunk_id=khoan.id,
                            content=content_with_context,
                            parent_id=dieu.id,
                            chunk_type="KHOAN",
                            metadata=base_metadata
                        ))
                    else:
                        # Fallback
                        chunks.extend(self._sliding_window_fallback(f"({dieu.title}) {full_khoan_text}", base_metadata, khoan.id, "KHOAN"))
                    continue
                
                # [3] Nếu cấp KHOẢN vượt giới hạn -> Tách cấp ĐIỂM
                khoan_header = f"({dieu.title}) {khoan.content}"
                if khoan.content.strip():
                    chunks.append(Chunk(
                        chunk_id=f"{khoan.id}_header",
                        content=khoan_header,
                        parent_id=khoan.id,
                        chunk_type="KHOAN_HEADER",
                        metadata=base_metadata
                    ))
                    
                for diem in khoan.diem_list:
                    diem_text = f"({dieu.title} - Khoản {khoan.id.split('_')[-1]}) {diem.content}"
                    if self._count_words(diem_text) <= self.max_words:
                        chunks.append(Chunk(
                            chunk_id=diem.id,
                            content=diem_text,
                            parent_id=khoan.id,
                            chunk_type="DIEM",
                            metadata=base_metadata
                        ))
                    else:
                        chunks.extend(self._sliding_window_fallback(diem_text, base_metadata, diem.id, "DIEM"))
                        
        return chunks

import re
import logging
from typing import List, Optional
from shared.models.schemas import LegalDocument, Chuong, Dieu, Khoan, Diem

logger = logging.getLogger(__name__)

class LegalStructureParser:
    def __init__(self):
        # Regex patterns to detect the start of sections
        self.chuong_pattern = re.compile(r'^(Chương\s+[IVXLCDM]+(?:[\.\:]\s*(.*))?)', re.IGNORECASE)
        self.dieu_pattern = re.compile(r'^(Điều\s+\d+\.)(?:(.*))?', re.IGNORECASE)
        self.khoan_pattern = re.compile(r'^(\d+)\.\s+(.*)')
        self.diem_pattern = re.compile(r'^([a-z])\)\s+(.*)')
        
    def parse(self, text: str) -> LegalDocument:
        """
        Phân tích cú pháp văn bản đã được clean thành cây cấu trúc LegalDocument
        """
        lines = text.split('\n')
        
        document = LegalDocument()
        
        current_chuong: Optional[Chuong] = None
        current_dieu: Optional[Dieu] = None
        current_khoan: Optional[Khoan] = None
        
        # Biến tạm để lưu trữ nội dung không thuộc các mục trên (vd: header)
        preamble = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for Chương
            chuong_match = self.chuong_pattern.match(line)
            if chuong_match:
                # Bắt đầu một chương mới
                chuong_title = line
                chuong_id = chuong_match.group(1).split()[1] if len(chuong_match.group(1).split()) > 1 else str(len(document.chuong_list) + 1)
                
                current_chuong = Chuong(id=f"chuong_{chuong_id}", title=chuong_title, dieu_list=[])
                document.chuong_list.append(current_chuong)
                
                current_dieu = None
                current_khoan = None
                continue
                
            # Check for Điều
            dieu_match = self.dieu_pattern.match(line)
            if dieu_match:
                dieu_id_str = dieu_match.group(1).replace('Điều', '').replace('.', '').strip()
                title_content = (dieu_match.group(2) or "").strip()
                
                current_dieu = Dieu(id=f"dieu_{dieu_id_str}", title=line, content="", khoan_list=[])
                if current_chuong:
                    current_chuong.dieu_list.append(current_dieu)
                else:
                    # Trường hợp không có chương, giả định tạo chương ảo hoặc đưa thẳng vào document
                    # Ở đây tạo một chương ảo "Chương 0"
                    current_chuong = Chuong(id="chuong_0", title="Không có chương", dieu_list=[current_dieu])
                    document.chuong_list.append(current_chuong)
                    
                current_khoan = None
                
                # Nếu có phần nội dung ngay sau title của điều (không chia khoản)
                if title_content:
                    current_dieu.content += title_content + "\n"
                continue
                
            # Check for Khoản
            khoan_match = self.khoan_pattern.match(line)
            if khoan_match and current_dieu is not None:
                khoan_id = khoan_match.group(1)
                content = line # Giữ nguyên cả dòng
                
                current_khoan = Khoan(id=f"{current_dieu.id}_khoan_{khoan_id}", content=content, diem_list=[])
                current_dieu.khoan_list.append(current_khoan)
                continue
                
            # Check for Điểm
            diem_match = self.diem_pattern.match(line)
            if diem_match and current_khoan is not None:
                diem_id = diem_match.group(1)
                content = line
                
                current_diem = Diem(id=f"{current_khoan.id}_diem_{diem_id}", content=content)
                current_khoan.diem_list.append(current_diem)
                continue
                
            # Content continuation
            if current_khoan and current_khoan.diem_list:
                current_khoan.diem_list[-1].content += "\n" + line
            elif current_khoan:
                current_khoan.content += "\n" + line
            elif current_dieu:
                current_dieu.content += "\n" + line
            else:
                preamble.append(line)
                
        # Làm sạch lại các nội dung
        for c in document.chuong_list:
            for d in c.dieu_list:
                d.content = d.content.strip()
                for k in d.khoan_list:
                    k.content = k.content.strip()
                    for diem in k.diem_list:
                        diem.content = diem.content.strip()
                        
        return document

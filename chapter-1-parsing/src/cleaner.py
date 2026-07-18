import re
import logging

logger = logging.getLogger(__name__)

class LegalCleaner:
    def __init__(self):
        # Mẫu regex để bảo vệ các pattern luật
        self.protect_patterns = [
            r'Chương\s+[IVXLCDM]+',
            r'Điều\s+\d+\.',
            r'\d+\.\s+',
            r'[a-z]\)\s+'
        ]
        
    def clean(self, raw_text: str) -> str:
        """
        Làm sạch raw_text:
        - Xóa khoảng trắng thừa
        - Nối các dòng bị ngắt sai (không phải bắt đầu bằng pattern Điều/Khoản/Điểm)
        """
        lines = raw_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Kiểm tra xem dòng này có bắt đầu bằng một legal pattern không
            is_legal_start = any(re.match(pattern, line, re.IGNORECASE) for pattern in self.protect_patterns)
            
            if is_legal_start:
                cleaned_lines.append(line)
            else:
                # Nếu không, có thể là dòng tiếp theo của đoạn trước đó
                # Kiểm tra xem dòng trước đó có kết thúc bằng dấu câu không
                if cleaned_lines and not re.search(r'[.:;]$', cleaned_lines[-1]):
                    cleaned_lines[-1] += " " + line
                else:
                    cleaned_lines.append(line)
                    
        return '\n'.join(cleaned_lines)

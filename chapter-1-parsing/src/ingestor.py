from abc import ABC, abstractmethod
import os

class BaseIngestor(ABC):
    @abstractmethod
    def read_text(self, file_path: str) -> str:
        pass

class MockPyMuPDFIngestor(BaseIngestor):
    """
    Simulation Layer cho PyMuPDF.
    Trong thực tế, lớp này sẽ dùng thư viện fitz (PyMuPDF) để extract text từ PDF 
    hoặc python-docx để đọc DOCX. Hiện tại mô phỏng đọc từ file text phẳng để đơn giản hóa MVP.
    """
    def read_text(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

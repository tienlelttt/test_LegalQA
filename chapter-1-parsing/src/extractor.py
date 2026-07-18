import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from shared.models.schemas import LegalDocument, Metadata

class MetadataExtractorInterface(ABC):
    @abstractmethod
    def extract_metadata(self, raw_text: str, document: LegalDocument) -> LegalDocument:
        pass

class RegexMetadataExtractor(MetadataExtractorInterface):
    def __init__(self):
        self.citation_pattern = re.compile(
            r'(Khoản\s+\d+\s+)?Điều\s+\d+\s+(của\s+)?(Luật|Nghị định|Thông tư)\s+[^,.]+',
            re.IGNORECASE
        )
        self.doc_id_pattern = re.compile(r'Số:\s*([0-9]+/[0-9]+/[A-Z0-9]+)')
        
    def extract_metadata(self, raw_text: str, document: LegalDocument) -> LegalDocument:
        metadata = Metadata()
        lines = raw_text.split('\n')[:50]
        for line in lines:
            match = self.doc_id_pattern.search(line)
            if match:
                metadata.document_id = match.group(1)
                break
                
        citations_set = set()
        for match in self.citation_pattern.finditer(raw_text):
            citations_set.add(match.group(0).strip())
            
        metadata.citations = list(citations_set)
        document.metadata = metadata
        return document

class MockLLMMetadataExtractor(MetadataExtractorInterface):
    """
    Simulation Layer for LLM Metadata Extraction.
    Trong thực tế, lớp này sẽ gọi Gemini/OpenAI API với JSON schema để trích xuất
    title, effective_date, status và các quan hệ phức tạp.
    """
    def __init__(self, base_extractor: MetadataExtractorInterface):
        self.base_extractor = base_extractor
        
    def extract_metadata(self, raw_text: str, document: LegalDocument) -> LegalDocument:
        # Chạy regex trước để lấy số hiệu và trích dẫn cơ bản
        document = self.base_extractor.extract_metadata(raw_text, document)
        
        # Mô phỏng LLM trả về các trường nâng cao
        document.metadata.title = f"Văn bản pháp luật {document.metadata.document_id}" if document.metadata.document_id else "Văn bản không rõ số hiệu"
        document.metadata.effective_date = "2024-01-01"
        document.metadata.issuing_body = "Cơ quan nhà nước có thẩm quyền"
        document.metadata.status = "effective"
        
        return document

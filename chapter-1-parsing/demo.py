import sys
import os
import io

# Add parent directory to sys.path to allow importing from 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ràng buộc cấu hình tiếng Việt cho console (Fix UnicodeEncodeError)
if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from src.ingestor import MockPyMuPDFIngestor
from src.cleaner import LegalCleaner
from src.parser import LegalStructureParser
from src.extractor import RegexMetadataExtractor, MockLLMMetadataExtractor
from src.chunker import AdaptiveChunker
from shared.paths import get_mock_file

ingestor = MockPyMuPDFIngestor()
MOCK_LUAT_DAT_DAI = ingestor.read_text(str(get_mock_file("luat_dat_dai.txt")))


def main():
    print("="*50)
    print("DEMO: HỆ THỐNG PARSING VÀ CHUNKING VĂN BẢN PHÁP LUẬT")
    print("="*50)
    
    print("\n[1] Văn bản gốc:")
    print("-" * 30)
    print(MOCK_LUAT_DAT_DAI[:300] + "...\n")
    
    print("\n[2] Thực hiện Cleaning...")
    cleaner = LegalCleaner()
    cleaned_text = cleaner.clean(MOCK_LUAT_DAT_DAI)
    
    print("\n[3] Phân tích cấu trúc (Parsing)...")
    parser = LegalStructureParser()
    doc = parser.parse(cleaned_text)
    
    print(f"-> Phân tích thành công {len(doc.chuong_list)} Chương")
    for chuong in doc.chuong_list:
        print(f"  + {chuong.title} ({len(chuong.dieu_list)} Điều)")
        
    print("\n[4] Trích xuất Metadata & Viện dẫn...")
    base_extractor = RegexMetadataExtractor()
    extractor = MockLLMMetadataExtractor(base_extractor)
    doc = extractor.extract_metadata(cleaned_text, doc)
    
    print(f"-> Số hiệu văn bản: {doc.metadata.document_id}")
    print(f"-> Tên văn bản: {doc.metadata.title}")
    print(f"-> Trạng thái: {doc.metadata.status}")
    print(f"-> Viện dẫn tìm thấy: {doc.metadata.citations}")
    
    print("\n[5] Adaptive Chunking (v2)...")
    chunker = AdaptiveChunker(max_words=200)
    chunks = chunker.chunk(doc)
    
    print(f"-> Tạo thành công {len(chunks)} chunks.")
    print("-" * 30)
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1} | ID: {chunk.chunk_id} | Type: {chunk.chunk_type}")
        print(f"Metadata: prev={chunk.metadata.get('prev_dieu_id')}, next={chunk.metadata.get('next_dieu_id')}")
        print(f"Content preview: {chunk.content[:60].replace(chr(10), ' ')}...")
        print("-" * 30)
        
    print("\nHOÀN THÀNH DEMO!")

if __name__ == "__main__":
    main()

import sys
import os
import time
import tracemalloc
from src.cleaner import LegalCleaner
from src.parser import LegalStructureParser
from src.extractor import RegexMetadataExtractor
from src.chunker import AdaptiveChunker
from shared.paths import get_mock_file

with open(get_mock_file("luat_dat_dai.txt"), "r", encoding="utf-8") as f:
    MOCK_LUAT_DAT_DAI = f.read()
with open(get_mock_file("bo_luat_dan_su.txt"), "r", encoding="utf-8") as f:
    MOCK_BO_LUAT_DAN_SU = f.read()

def run_benchmark():
    texts = [MOCK_LUAT_DAT_DAI, MOCK_BO_LUAT_DAN_SU] * 50 # Giả lập dữ liệu lớn
    full_text = "\n\n".join(texts)
    
    print(f"Bắt đầu benchmark với {len(texts)} văn bản (tổng {len(full_text)} ký tự)")
    
    # Bắt đầu đo bộ nhớ và thời gian
    tracemalloc.start()
    start_time = time.time()
    
    cleaner = LegalCleaner()
    parser = LegalStructureParser()
    extractor = RegexMetadataExtractor()
    chunker = AdaptiveChunker()
    
    cleaned_text = cleaner.clean(full_text)
    doc = parser.parse(cleaned_text)
    doc = extractor.extract_metadata(cleaned_text, doc)
    chunks = chunker.chunk(doc)
    
    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Kết quả
    exec_time = end_time - start_time
    print(f"Tổng số chunks sinh ra: {len(chunks)}")
    print(f"Thời gian thực thi: {exec_time:.4f} giây")
    print(f"Bộ nhớ tiêu thụ tối đa: {peak / 10**6:.4f} MB")
    print(f"Throughput: {len(full_text) / exec_time / 10**6:.4f} MB/s")

if __name__ == "__main__":
    run_benchmark()

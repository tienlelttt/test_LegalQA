import os
from pathlib import Path

# Root của toàn bộ project LegalQA
PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Single Source of Truth cho toàn bộ dữ liệu
DATA_DIR = PROJECT_ROOT / "data"

# Phân cấp thư mục dữ liệu
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MOCK_DATA_DIR = DATA_DIR / "mock"
BENCHMARK_DATA_DIR = DATA_DIR / "benchmark"
SAMPLE_QUERIES_DIR = DATA_DIR / "sample_queries"

# Helper function để lấy nhanh đường dẫn của một file mock cụ thể
def get_mock_file(filename: str) -> Path:
    return MOCK_DATA_DIR / filename

import pytest
import sys
import os
chapter_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if chapter_dir not in sys.path:
    sys.path.insert(0, chapter_dir)

from src.cleaner import LegalCleaner
from src.parser import LegalStructureParser

def test_cleaner():
    cleaner = LegalCleaner()
    raw_text = "Điều 1. Phạm vi \n điều chỉnh\nĐây là dòng \ntiếp theo."
    cleaned = cleaner.clean(raw_text)
    
    assert "Điều 1. Phạm vi điều chỉnh" in cleaned
    assert "Đây là dòng tiếp theo." in cleaned

def test_parser():
    parser = LegalStructureParser()
    text = "Chương I. QUY ĐỊNH CHUNG\nĐiều 1. Phạm vi điều chỉnh\nNội dung điều 1.\nĐiều 2. Đối tượng\n1. Cơ quan\n2. Người sử dụng"
    
    doc = parser.parse(text)
    
    assert len(doc.chuong_list) == 1
    chuong = doc.chuong_list[0]
    assert chuong.id == "chuong_I."
    
    assert len(chuong.dieu_list) == 2
    dieu1 = chuong.dieu_list[0]
    assert dieu1.id == "dieu_1"
    assert "Nội dung điều 1." in dieu1.content
    
    dieu2 = chuong.dieu_list[1]
    assert dieu2.id == "dieu_2"
    assert len(dieu2.khoan_list) == 2
    assert "Cơ quan" in dieu2.khoan_list[0].content

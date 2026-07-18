from typing import List, Union, Optional
from sentence_transformers import SentenceTransformer
import torch

class LegalEmbedder:
    """
    Lớp mã hóa (Embedding) văn bản pháp luật bằng Dense Vectors.
    Sử dụng SentenceTransformers (mặc định: paraphrase-multilingual-MiniLM-L12-v2).
    """
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device: Optional[str] = None):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"Loading embedding model '{model_name}' on {self.device}...")
        self.model = SentenceTransformer(model_name, device=self.device)
        print("Model loaded successfully.")
        
    def embed_text(self, text: str) -> List[float]:
        """
        Mã hóa một đoạn văn bản thành vector.
        """
        vector = self.model.encode(text, convert_to_numpy=True)
        return vector.tolist()
        
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Mã hóa một danh sách đoạn văn bản thành danh sách vector (tối ưu tốc độ).
        """
        vectors = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        return vectors.tolist()

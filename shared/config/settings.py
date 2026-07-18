import os
from pydantic import BaseModel

class AppSettings(BaseModel):
    # Embedding Configuration
    EMBEDDING_TOKEN_LIMIT: int = int(os.getenv("EMBEDDING_TOKEN_LIMIT", "512"))
    MAX_WORDS: int = int(EMBEDDING_TOKEN_LIMIT * 0.75)
    
    # Vector DB Configuration (Development Profile by default)
    QDRANT_LOCATION: str = os.getenv("QDRANT_LOCATION", ":memory:")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "legalqa_index")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    VECTOR_SIZE: int = int(os.getenv("VECTOR_SIZE", "384"))
    
    DEBUG_MODE: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Query Pipeline (Chapter 3) Configuration
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "30"))
    RERANKER_TOP_K: int = int(os.getenv("RERANKER_TOP_K", "5"))
    RRF_K: int = int(os.getenv("RRF_K", "60"))
    
    RERANKER_MODEL_NAME: str = os.getenv("RERANKER_MODEL_NAME", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    LLM_MAX_CONTEXT_TOKENS: int = int(os.getenv("LLM_MAX_CONTEXT_TOKENS", "4096"))
    
settings = AppSettings()

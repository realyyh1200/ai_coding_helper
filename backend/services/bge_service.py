from core.logger import logger
import os
import hashlib
from typing import List


class BGEEmbeddingService:
    _instance = None
    _model = None
    _fallback_dim = 512

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._model = None
        self._try_load_model()

    def _try_load_model(self) -> None:
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bge_model")
        try:
            if os.path.exists(model_path) and any(os.listdir(model_path)):
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading BGE model from local path: {model_path}")
                self._model = SentenceTransformer(model_path)
                logger.info(f"BGE model loaded successfully, embedding dimension: {self._model.get_sentence_embedding_dimension()}")
            else:
                logger.info("BGE model not found locally, using fallback embedding")
        except Exception as e:
            logger.warning(f"Failed to load BGE model, using fallback embedding: {e}")
            self._model = None

    def _fallback_embedding(self, text: str) -> List[float]:
        """备用向量化方法：使用哈希生成固定维度向量"""
        vector = [0.0] * self._fallback_dim
        text_bytes = text.encode('utf-8')
        for i in range(self._fallback_dim):
            hash_val = int(hashlib.md5(text_bytes + bytes([i])).hexdigest(), 16)
            vector[i] = (hash_val % 1000) / 1000.0 - 0.5
        return vector

    @property
    def embedding_dim(self) -> int:
        if self._model is not None:
            return self._model.get_sentence_embedding_dimension()
        return self._fallback_dim

    def encode(self, texts: str | List[str], normalize: bool = True) -> List[List[float]]:
        if isinstance(texts, str):
            texts = [texts]
        try:
            if self._model is not None:
                embeddings = self._model.encode(texts, normalize_embeddings=normalize)
                return embeddings.tolist()
            else:
                return [self._fallback_embedding(text) for text in texts]
        except Exception as e:
            logger.error(f"Failed to encode texts: {e}")
            return [self._fallback_embedding(text) for text in texts]

    def encode_query(self, query: str) -> List[float]:
        return self.encode([query])[0]


bge_service = BGEEmbeddingService()

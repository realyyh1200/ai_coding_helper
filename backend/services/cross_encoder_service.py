from sentence_transformers import CrossEncoder
from core.logger import logger
import os

class CrossEncoderService:
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """初始化Cross-Encoder模型用于精排"""
        self.model = None
        try:
            model_cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cross_encoder_model')
            os.makedirs(model_cache_dir, exist_ok=True)

            self.model = CrossEncoder(
                model_name,
                cache_folder=model_cache_dir
            )
            logger.info("✅ Cross-encoder模型加载完成: {}".format(model_name))
        except Exception as e:
            logger.error(f"❌ Cross-encoder模型加载失败: {str(e)}")
            logger.info("⚠️ 将跳过cross-encoder精排，仅使用BM25+余弦相似度召回")

    def score(self, query: str, documents: list) -> list:
        """为query和每个document计算相关性分数"""
        if not self.model or not documents:
            return [0.0] * len(documents)

        try:
            pairs = [(query, doc) for doc in documents]
            scores = self.model.predict(pairs)
            return scores.tolist()
        except Exception as e:
            logger.error(f"❌ Cross-encoder评分失败: {str(e)}")
            return [0.0] * len(documents)
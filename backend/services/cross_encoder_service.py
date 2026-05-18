from core.logger import logger
import os
import threading
from pathlib import Path

class CrossEncoderService:
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2', timeout: int = 1800):
        """初始化Cross-Encoder模型用于精排"""
        self.model = None
        self.loading_error = None
        self.timeout = timeout
        
        self._load_model_with_timeout(model_name, timeout)

    def _check_local_model(self, model_name: str) -> str:
        """检查本地是否有模型"""
        local_cache_dir = Path(__file__).parent.parent / 'cross_encoder_model'
        expected_model_path = local_cache_dir / f"models--{model_name.replace('/', '--')}"
        
        if expected_model_path.exists():
            snapshots_dir = expected_model_path / 'snapshots'
            if snapshots_dir.exists():
                snapshot_folders = list(snapshots_dir.iterdir())
                if snapshot_folders:
                    model_dir = snapshot_folders[0]
                    config_file = model_dir / 'config.json'
                    if config_file.exists():
                        logger.info(f"✅ 找到本地Cross-encoder模型: {model_dir}")
                        return str(model_dir)
        
        logger.info(f"⚠️ 本地未找到Cross-encoder模型，将尝试下载")
        return None

    def _load_model_with_timeout(self, model_name: str, timeout: int):
        """带超时的模型加载"""
        result = {'success': False, 'model': None, 'error': None}
        lock = threading.Lock()
        
        def load_model():
            try:
                from sentence_transformers import CrossEncoder
                
                model_path = self._check_local_model(model_name)
                
                if model_path:
                    model = CrossEncoder(model_path)
                else:
                    model_cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cross_encoder_model')
                    os.makedirs(model_cache_dir, exist_ok=True)
                    
                    logger.info(f"📥 正在下载Cross-encoder模型: {model_name} (超时: {timeout}秒)")
                    model = CrossEncoder(
                        model_name,
                        cache_folder=model_cache_dir
                    )
                    logger.info(f"✅ Cross-encoder模型下载并加载完成: {model_name}")
                
                with lock:
                    result['success'] = True
                    result['model'] = model
                    logger.info("✅ Cross-encoder模型加载完成")
            except Exception as e:
                with lock:
                    result['error'] = str(e)
                logger.error(f"❌ Cross-encoder模型加载失败: {str(e)}")

        thread = threading.Thread(target=load_model)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            logger.error(f"❌ Cross-encoder模型加载超时 ({timeout}秒)")
            self.loading_error = "加载超时"
            logger.info("⚠️ 将跳过cross-encoder精排，仅使用BM25+余弦相似度召回")
        else:
            with lock:
                if result['success']:
                    self.model = result['model']
                else:
                    self.loading_error = result['error']
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
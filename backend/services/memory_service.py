from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from models.memory import UserMemory
from models.user import User, Conversation, Message
from services.qdrant_service import qdrant_service
from services.bge_service import bge_service
from datetime import datetime, timedelta
from collections import OrderedDict, Counter
from core.logger import logger
import math
import json
import re


class BM25Retrieval:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = 0
        self.avg_doc_len = 0
        self.doc_term_freqs: List[Dict[str, int]] = []
        self.doc_lens: List[int] = []
        self.idf: Dict[str, float] = {}
        self.doc_count_per_term: Dict[str, int] = {}
        self.doc_ids: List[int] = []
        self._jieba_available = False
        self._init_jieba()

    def _init_jieba(self) -> None:
        """尝试初始化 jieba 分词器"""
        try:
            import jieba
            self._jieba = jieba
            self._jieba_available = True
            logger.info("✅ jieba 分词器已加载")
        except ImportError:
            self._jieba_available = False
            logger.warning("⚠️ jieba 未安装，将使用字符级分词处理中文")

    def _contains_chinese(self, text: str) -> bool:
        """检测文本是否包含中文"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    def tokenize(self, text: str) -> List[str]:
        text = text.lower()
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            '我', '你', '他', '她', '它', '我们', '你们', '他们', '的', '了', '在',
            '是', '有', '和', '就', '不', '人', '都', '一', '一个', '上',
            '也', '很', '到', '说', '要', '去', '会', '着', '没有', '看',
            '好', '自己', '这', '那', '么', '什么', '怎么', '为什么'
        }

        if self._contains_chinese(text):
            # 中文文本使用 jieba 分词
            if self._jieba_available:
                tokens = self._jieba.lcut(text)
            else:
                # 降级为字符级分词
                tokens = list(text)
        else:
            # 纯英文文本使用正则分词
            tokens = re.findall(r'\b\w+\b', text)

        return [t for t in tokens if t not in stop_words and len(t) > 1]

    def add_document(self, doc_id: int, doc_text: str) -> None:
        tokens = self.tokenize(doc_text)
        tf = Counter(tokens)
        self.doc_term_freqs.append(dict(tf))
        self.doc_lens.append(len(tokens))
        self.doc_ids.append(doc_id)
        for term in tf.keys():
            self.doc_count_per_term[term] = self.doc_count_per_term.get(term, 0) + 1
        self.doc_count += 1
        self.avg_doc_len = sum(self.doc_lens) / self.doc_count if self.doc_count > 0 else 0

    def calculate_idf(self) -> None:
        for term, doc_count in self.doc_count_per_term.items():
            self.idf[term] = math.log((self.doc_count - doc_count + 0.5) / (doc_count + 0.5) + 1)

    def score(self, query_tokens: List[str], doc_idx: int) -> float:
        if doc_idx >= len(self.doc_term_freqs):
            return 0.0
        doc_tf = self.doc_term_freqs[doc_idx]
        doc_len = self.doc_lens[doc_idx]
        score = 0.0
        for term in query_tokens:
            if term not in doc_tf:
                continue
            tf = doc_tf[term]
            idf = self.idf.get(term, 0)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            score += idf * (numerator / denominator) if denominator > 0 else 0
        return score

    def batch_score(self, query_tokens: List[str]) -> List[Tuple[int, float]]:
        scores = []
        for i in range(self.doc_count):
            doc_id = self.doc_ids[i]
            score = self.score(query_tokens, i)
            if score > 0:
                scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


class CosineSimilarity:
    @staticmethod
    def compute(vec1: List[float], vec2: List[float]) -> float:
        if not vec1 or not vec2:
            return 0.0
        min_len = min(len(vec1), len(vec2))
        vec1 = vec1[:min_len]
        vec2 = vec2[:min_len]
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot_product / (mag1 * mag2)


class HybridRetrievalService:
    def __init__(self, db: Session, user_id: int, alpha: float = 0.7):
        self.db = db
        self.user_id = user_id
        self.alpha = alpha
        self.bm25 = BM25Retrieval()
        self._initialize_bm25()

    def _initialize_bm25(self) -> None:
        memories = self.db.query(UserMemory).filter(
            UserMemory.user_id == self.user_id,
            UserMemory.is_active == True
        ).all()
        for memory in memories:
            self.bm25.add_document(memory.id, memory.content)
        self.bm25.calculate_idf()

    def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: str = None,
        conversation_id: int = None
    ) -> List[Tuple[UserMemory, float, str]]:
        query_tokens = self.bm25.tokenize(query)
        bm25_scores = self.bm25.batch_score(query_tokens)

        query_embedding = bge_service.encode_query(query)
        qdrant_results = []
        if qdrant_service.is_connected():
            qdrant_results = qdrant_service.search_vectors(
                query_vector=query_embedding,
                user_id=self.user_id,
                limit=top_k * 2,
                score_threshold=0.3
            )

        memories = self.db.query(UserMemory).filter(
            UserMemory.user_id == self.user_id,
            UserMemory.is_active == True
        )
        if memory_type:
            memories = memories.filter(UserMemory.memory_type == memory_type)
        if conversation_id:
            memories = memories.filter(UserMemory.conversation_id == conversation_id)
        memories = {m.id: m for m in memories.all()}

        hybrid_scores: Dict[int, float] = {}
        hybrid_sources: Dict[int, str] = {}

        for memory_id, bm25_score in bm25_scores:
            if memory_id in memories:
                hybrid_scores[memory_id] = hybrid_scores.get(memory_id, 0) + (1 - self.alpha) * bm25_score
                hybrid_sources[memory_id] = 'bm25'

        for result in qdrant_results:
            memory_id = result['payload'].get('memory_id')
            cosine_score = result['score']
            if memory_id in memories and cosine_score > 0.3:
                hybrid_scores[memory_id] = hybrid_scores.get(memory_id, 0) + self.alpha * cosine_score
                hybrid_sources[memory_id] = 'qdrant'

        sorted_scores = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for memory_id, score in sorted_scores[:top_k]:
            if memory_id in memories:
                results.append((memories[memory_id], score, hybrid_sources.get(memory_id, 'unknown')))
        return results

    def add_memory(
        self,
        content: str,
        memory_type: str = "general",
        importance: int = 1,
        conversation_id: int = None,
        metadata: dict = None
    ) -> UserMemory:
        bm25_tokens = self.bm25.tokenize(content)
        embedding = bge_service.encode_query(content)

        memory = UserMemory(
            user_id=self.user_id,
            conversation_id=conversation_id,
            memory_type=memory_type,
            content=content,
            keywords=bm25_tokens,
            importance=importance,
            metadata=metadata or {}
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)

        self.bm25.add_document(memory.id, content)

        if qdrant_service.is_connected():
            qdrant_service.upsert_vector(
                user_id=self.user_id,
                memory_id=memory.id,
                vector=embedding,
                payload={
                    "memory_type": memory_type,
                    "content": content[:500],
                    "importance": importance,
                    "conversation_id": conversation_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            )

        logger.info(f"HybridRetrieval: Added memory id={memory.id}, type={memory_type}")
        return memory

    def update_access(self, memory_id: int) -> None:
        memory = self.db.query(UserMemory).filter(UserMemory.id == memory_id).first()
        if memory:
            memory.access_count += 1
            memory.last_accessed_at = datetime.utcnow()
            self.db.commit()

    def delete_memory(self, memory_id: int) -> bool:
        if qdrant_service.is_connected():
            qdrant_service.delete_vectors(memory_id, self.user_id)
        memory = self.db.query(UserMemory).filter(UserMemory.id == memory_id).first()
        if memory:
            memory.is_active = False
            self.db.commit()
            return True
        return False


class ShortTermMemory:
    def __init__(self, max_size: int = 10, ttl_seconds: int = 1800):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._memory: OrderedDict[str, dict] = OrderedDict()

    def add(self, key: str, item: dict) -> None:
        if key in self._memory:
            del self._memory[key]
        item['created_at'] = datetime.utcnow()
        self._memory[key] = item
        if len(self._memory) > self.max_size:
            self._memory.popitem(last=False)

    def get(self, key: str) -> Optional[dict]:
        item = self._memory.get(key)
        if item and self._is_expired(item):
            del self._memory[key]
            return None
        return item

    def get_all(self) -> List[dict]:
        self._cleanup_expired()
        return list(self._memory.values())

    def _is_expired(self, item: dict) -> bool:
        return (datetime.utcnow() - item['created_at']).total_seconds() > self.ttl_seconds

    def _cleanup_expired(self) -> None:
        expired_keys = [k for k, v in self._memory.items() if self._is_expired(v)]
        for k in expired_keys:
            del self._memory[k]


class LongTermMemory:
    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        user_id: int,
        conversation_id: Optional[int],
        content: str,
        memory_type: str = "general",
        importance: int = 1,
        metadata: dict = None
    ) -> UserMemory:
        tokens = BM25Retrieval().tokenize(content)

        memory = UserMemory(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            keywords=tokens,
            metadata=metadata or {}
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)

        embedding = bge_service.encode_query(content)
        if qdrant_service.is_connected():
            qdrant_service.upsert_vector(
                user_id=user_id,
                memory_id=memory.id,
                vector=embedding,
                payload={
                    "memory_type": memory_type,
                    "content": content[:500],
                    "importance": importance,
                    "conversation_id": conversation_id
                }
            )

        return memory

    def get_user_memories(
        self,
        user_id: int,
        memory_type: str = None,
        limit: int = 50
    ) -> List[UserMemory]:
        query = self.db.query(UserMemory).filter(
            UserMemory.user_id == user_id,
            UserMemory.is_active == True
        )
        if memory_type:
            query = query.filter(UserMemory.memory_type == memory_type)
        return query.order_by(
            UserMemory.importance.desc(),
            UserMemory.last_accessed_at.desc(),
            UserMemory.created_at.desc()
        ).limit(limit).all()

    def get_conversation_memories(self, conversation_id: int) -> List[UserMemory]:
        return self.db.query(UserMemory).filter(
            UserMemory.conversation_id == conversation_id,
            UserMemory.is_active == True
        ).order_by(UserMemory.importance.desc(), UserMemory.created_at.desc()).all()

    def delete(self, memory_id: int) -> bool:
        memory = self.db.query(UserMemory).filter(UserMemory.id == memory_id).first()
        if not memory:
            return False
        memory.is_active = False
        self.db.commit()
        if qdrant_service.is_connected():
            qdrant_service.delete_vectors(memory_id, memory.user_id)
        return True

    def clear_conversation_memories(self, conversation_id: int) -> int:
        memories = self.db.query(UserMemory).filter(
            UserMemory.conversation_id == conversation_id
        ).all()

        for memory in memories:
            memory.is_active = False
            if qdrant_service.is_connected():
                qdrant_service.delete_vectors(memory.id, memory.user_id)

        self.db.commit()
        return len(memories)


class MemoryService:
    SHORT_TERM_MEMORY_MAX_SIZE = 10
    SHORT_TERM_MEMORY_TTL_SECONDS = 1800
    HYBRID_ALPHA = 0.7

    def __init__(self, db: Session, user_id: int, conversation_id: int = None):
        self.db = db
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.short_term = ShortTermMemory(
            max_size=self.SHORT_TERM_MEMORY_MAX_SIZE,
            ttl_seconds=self.SHORT_TERM_MEMORY_TTL_SECONDS
        )
        self.long_term = LongTermMemory(db)
        self.hybrid = HybridRetrievalService(db, user_id, alpha=self.HYBRID_ALPHA)
        logger.info(f"MemoryService initialized for user={user_id}, conversation={conversation_id}")

    def add_message(self, role: str, content: str) -> None:
        key = f"msg_{self.conversation_id}_{datetime.utcnow().timestamp()}"
        item = {
            "content": content,
            "type": "message",
            "role": role,
            "importance": 1
        }
        self.short_term.add(key, item)

        if role == "assistant":
            self.hybrid.add_memory(
                content=content,
                memory_type="learned",
                conversation_id=self.conversation_id,
                importance=1,
                metadata={"role": role}
            )
        logger.debug(f"MemoryService: Added message, role={role}")

    def add_learned_info(
        self,
        content: str,
        importance: int = 2,
        metadata: dict = None
    ) -> None:
        self.hybrid.add_memory(
            content=content,
            memory_type="learned",
            conversation_id=self.conversation_id,
            importance=importance,
            metadata=metadata
        )
        logger.info(f"MemoryService: Stored learned info, importance={importance}")

    def get_context_for_ai(self, include_recent: int = 5, hybrid_top_k: int = 3) -> str:
        context_parts = []
        context_parts.append("## 短期记忆 (当前对话)")
        recent_items = self.short_term.get_all()[-include_recent:]
        if recent_items:
            for i, item in enumerate(recent_items, 1):
                role = item.get('role', 'unknown')
                content = item.get('content', '')
                context_parts.append(f"{i}. [{role}] {content}")
        else:
            context_parts.append("(无)")

        context_parts.append("\n## 长期记忆 (语义检索)")
        query = " ".join([item['content'] for item in recent_items]) if recent_items else "对话 助手 AI"
        hybrid_results = self.hybrid.search(
            query=query,
            top_k=hybrid_top_k,
            memory_type="learned",
            conversation_id=self.conversation_id
        )
        if hybrid_results:
            for memory, score, source in hybrid_results:
                context_parts.append(f"- [{source}] {memory.content}")
        else:
            long_term_memories = self.long_term.get_user_memories(
                self.user_id, memory_type="learned", limit=5
            )
            if long_term_memories:
                for mem in long_term_memories:
                    context_parts.append(f"- [importance:{mem.importance}] {mem.content}")
            else:
                context_parts.append("(无)")

        result = "\n".join(context_parts)
        logger.debug(f"MemoryService: Generated context, length={len(result)}")
        return result

    def store_user_preference(self, key: str, value: Any) -> None:
        content = json.dumps({"key": key, "value": value})
        self.hybrid.add_memory(
            content=content,
            memory_type="preference",
            conversation_id=None,
            importance=3,
            metadata={"preference_key": key}
        )
        logger.info(f"MemoryService: Stored preference {key}={value}")

    def get_user_preferences(self) -> List[UserMemory]:
        return self.long_term.get_user_memories(self.user_id, memory_type="preference")

    def clear_conversation_memory(self) -> None:
        if self.conversation_id:
            self.short_term._memory.clear()
            self.long_term.clear_conversation_memories(self.conversation_id)
            logger.info(f"MemoryService: Cleared memory for conversation={self.conversation_id}")

    def get_memory_stats(self) -> dict:
        qdrant_count = 0
        if qdrant_service.is_connected():
            qdrant_count = qdrant_service.count_vectors(self.user_id)
        return {
            "short_term_count": len(self.short_term.get_all()),
            "long_term_user_memories": len(self.long_term.get_user_memories(self.user_id)),
            "long_term_conversation_memories": len(
                self.long_term.get_conversation_memories(self.conversation_id)
            ) if self.conversation_id else 0,
            "qdrant_vectors": qdrant_count,
            "bge_embedding_dim": bge_service.embedding_dim
        }

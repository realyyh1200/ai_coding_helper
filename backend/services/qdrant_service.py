from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Range, SearchRequest
from qdrant_client.http.exceptions import UnexpectedResponse
from core.config import settings
from core.logger import logger
from typing import List, Optional, Dict, Any
import uuid


class QdrantService:
    _instance = None
    _client: Optional[QdrantClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._connect()

    def _connect(self) -> None:
        try:
            self._client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=10
            )
            self._ensure_collection()
            logger.info(f"Qdrant connected: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self._client = None

    def _ensure_collection(self) -> None:
        if self._client is None:
            return
        try:
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]
            if settings.QDRANT_COLLECTION not in collection_names:
                self._client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=VectorParams(
                        size=settings.QDRANT_VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {settings.QDRANT_COLLECTION}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")

    def is_connected(self) -> bool:
        return self._client is not None

    def upsert_vector(
        self,
        user_id: int,
        memory_id: int,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> Optional[str]:
        if self._client is None:
            logger.warning("Qdrant not connected, skipping upsert")
            return None
        try:
            point_id = f"{user_id}_{memory_id}_{uuid.uuid4().hex[:8]}"
            self._client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "user_id": user_id,
                            "memory_id": memory_id,
                            **payload
                        }
                    )
                ]
            )
            logger.debug(f"Upserted vector: {point_id}")
            return point_id
        except Exception as e:
            logger.error(f"Failed to upsert vector: {e}")
            return None

    def search_vectors(
        self,
        query_vector: List[float],
        user_id: int,
        limit: int = 5,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        if self._client is None:
            logger.warning("Qdrant not connected, returning empty results")
            return []
        try:
            results = self._client.query_points(
                collection_name=settings.QDRANT_COLLECTION,
                query=SearchRequest(
                    vector=query_vector,
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="user_id",
                                match=MatchValue(value=user_id)
                            )
                        ]
                    ),
                    limit=limit,
                    score_threshold=score_threshold
                )
            )
            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "payload": r.payload
                }
                for r in results.points
            ]
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    def delete_vectors(self, memory_id: int, user_id: int) -> bool:
        if self._client is None:
            return False
        try:
            self._client.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="memory_id", match=MatchValue(value=memory_id)),
                        FieldCondition(key="user_id", match=MatchValue(value=user_id))
                    ]
                )
            )
            logger.debug(f"Deleted vectors for memory_id={memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    def delete_user_vectors(self, user_id: int) -> bool:
        if self._client is None:
            return False
        try:
            self._client.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id))
                    ]
                )
            )
            logger.info(f"Deleted all vectors for user_id={user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete user vectors: {e}")
            return False

    def count_vectors(self, user_id: int) -> int:
        if self._client is None:
            return 0
        try:
            result = self._client.count(
                collection_name=settings.QDRANT_COLLECTION,
                count_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id))
                    ]
                )
            )
            return result.count
        except Exception as e:
            logger.error(f"Failed to count vectors: {e}")
            return 0


qdrant_service = QdrantService()

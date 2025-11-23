import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

try:
    from pymongo import DESCENDING, MongoClient
    from pymongo.collection import Collection
    from pymongo.errors import PyMongoError
except ImportError:  # pragma: no cover - optional dependency
    MongoClient = None
    DESCENDING = None
    Collection = None
    PyMongoError = Exception

logger = logging.getLogger(__name__)


class HiveMindClient:
    """MongoDB Atlas connector that stores and queries DevScope activity logs."""

    def __init__(
        self,
        uri: Optional[str] = None,
        db_name: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self.uri = uri or os.environ.get("HIVEMIND_MONGO_URI")
        self.db_name = db_name or os.environ.get("HIVEMIND_MONGO_DB", "devscope")
        self.collection_name = collection_name or os.environ.get("HIVEMIND_COLLECTION", "activity_logs")
        self._client: Optional[MongoClient] = None
        self._collection: Optional[Collection] = None
        self._healthy: Optional[bool] = None

    @property
    def enabled(self) -> bool:
        """Return True if MongoDB connectivity is available."""
        if not self.uri or MongoClient is None:
            return False
        return self._ensure_connection() is not None

    def publish_activity(self, payload: Dict) -> bool:
        """
        Insert a textual activity document into the Hive Mind.

        Ensures screenshots or other binary blobs are never uploaded by stripping
        known image keys before writing to Mongo.
        """
        collection = self._ensure_connection()
        if collection is None:
            return False

        clean_payload = {k: v for k, v in payload.items() if k not in {"image_path", "screenshot"}}
        clean_payload.setdefault("created_at", datetime.utcnow())

        try:
            collection.insert_one(clean_payload)
            logger.debug(
                "Hive Mind upload succeeded for org=%s user=%s",
                clean_payload.get("org_id"),
                clean_payload.get("user_id"),
            )
            return True
        except PyMongoError as exc:  # pragma: no cover - dependent on network
            logger.warning("Failed to upload Hive Mind payload: %s", exc)
            return False

    def query_activity(
        self,
        org_id: str,
        scope: str = "org",
        project_name: Optional[str] = None,
        limit: int = 40,
    ) -> List[Dict]:
        """Fetch recent activity entries scoped to an org or project."""
        collection = self._ensure_connection()
        if collection is None or not org_id:
            return []

        query: Dict = {"org_id": org_id}
        if scope == "project" and project_name:
            query["project_name"] = project_name

        try:
            cursor = (
                collection.find(query)
                .sort("timestamp", DESCENDING or -1)
                .limit(max(limit, 1))
            )
            return list(cursor)
        except PyMongoError as exc:  # pragma: no cover
            logger.warning("Hive Mind query failed: %s", exc)
            return []

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._collection = None

    def _ensure_connection(self) -> Optional[Collection]:
        if self._collection is not None:
            return self._collection

        if not self.uri or MongoClient is None:
            if self._healthy is None:
                logger.info("Hive Mind disabled: missing pymongo or HIVEMIND_MONGO_URI.")
                self._healthy = False
            return None

        try:
            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=4000)
            self._client.admin.command("ping")
            db = self._client[self.db_name]
            self._collection = db[self.collection_name]
            self._healthy = True
            logger.info("Hive Mind connected to %s/%s", self.db_name, self.collection_name)
        except Exception as exc:  # pragma: no cover
            logger.warning("Unable to connect to Hive Mind: %s", exc)
            self._client = None
            self._collection = None
            self._healthy = False

        return self._collection

    def __del__(self) -> None:  # pragma: no cover - destructor safety
        try:
            self.close()
        except Exception:
            pass


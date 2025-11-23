import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from constants import DEFAULT_ORG_ID

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
        summaries_collection_name: Optional[str] = None,
    ) -> None:
        self.uri = uri or os.environ.get("HIVEMIND_MONGO_URI")
        self.db_name = db_name or os.environ.get("HIVEMIND_MONGO_DB", "devscope")
        self.collection_name = collection_name or os.environ.get("HIVEMIND_COLLECTION", "activity_logs")
        self.summaries_collection_name = summaries_collection_name or os.environ.get(
            "HIVEMIND_SUMMARIES_COLLECTION", "session_summaries"
        )
        self._client: Optional[MongoClient] = None
        self._collection: Optional[Collection] = None
        self._summaries_collection: Optional[Collection] = None
        self._healthy: Optional[bool] = None
        self._default_org = DEFAULT_ORG_ID

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
        clean_payload.setdefault("org_id", self._default_org)

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
        org_id: Optional[str] = None,
        scope: str = "org",
        project_name: Optional[str] = None,
        limit: int = 40,
        since: Optional[datetime] = None,
    ) -> List[Dict]:
        """Fetch recent activity entries scoped to an org or project."""
        collection = self._ensure_connection()
        if collection is None:
            return []

        query: Dict = {"org_id": org_id or self._default_org}
        if scope == "project" and project_name:
            query["project_name"] = project_name
        if since:
            query["timestamp"] = {"$gte": since}

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

    def save_summary(self, document: Dict) -> bool:
        """
        Persist a session-level summary document (standup/batch reports).
        """
        collection = self._ensure_summaries_collection()
        if collection is None:
            return False
        try:
            collection.insert_one(document)
            logger.debug(
                "Session summary stored for org=%s user=%s session=%s",
                document.get("org_id"),
                document.get("user_id"),
                document.get("session_id"),
            )
            return True
        except PyMongoError as exc:  # pragma: no cover
            logger.warning("Failed to store session summary: %s", exc)
            return False

    def query_summaries(
        self,
        org_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict]:
        """Fetch recent high-level session summaries for an org."""
        collection = self._ensure_summaries_collection()
        if collection is None:
            return []

        try:
            cursor = (
                collection.find({"org_id": org_id or self._default_org})
                .sort("timestamp", DESCENDING or -1)
                .limit(max(limit, 1))
            )
            return list(cursor)
        except PyMongoError as exc:  # pragma: no cover
            logger.warning("Hive Mind summary query failed: %s", exc)
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

    def _ensure_summaries_collection(self) -> Optional[Collection]:
        if self._summaries_collection is not None:
            return self._summaries_collection

        collection = self._ensure_connection()
        if collection is None or not self._client:
            return None

        try:
            db = self._client[self.db_name]
            self._summaries_collection = db[self.summaries_collection_name]
        except Exception as exc:  # pragma: no cover
            logger.warning("Unable to access summaries collection: %s", exc)
            self._summaries_collection = None

        return self._summaries_collection

    def __del__(self) -> None:  # pragma: no cover - destructor safety
        try:
            self.close()
        except Exception:
            pass


# Backwards-compatible alias
AtlasClient = HiveMindClient


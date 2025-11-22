import logging
import os
from typing import Optional

from api_models import create_model
from hivemind import HiveMindClient

logger = logging.getLogger(__name__)


class OracleService:
    """Natural-language QA over the Hive Mind activity logs."""

    def __init__(
        self,
        hivemind: HiveMindClient,
        model_name: str = "gemini-2.0-flash",
        max_context: int = 40,
    ) -> None:
        self.hivemind = hivemind
        self.model = create_model(model_name)
        self.max_context = max_context
        self.default_org_id = os.environ.get("HIVEMIND_ORG_ID", "")

    def ask(self, question: str, scope: str = "org", project_name: Optional[str] = None) -> str:
        question = question.strip()
        if not question:
            return "Please enter a question for the Oracle."

        if not self.hivemind or not self.hivemind.enabled:
            return "Hive Mind is not configured. Set HIVEMIND_MONGO_URI to enable Oracle."

        org_id = self.default_org_id
        if not org_id:
            return "Oracle is missing HIVEMIND_ORG_ID."

        scope_key = scope if scope in {"project", "org"} else "org"
        logs = self.hivemind.query_activity(
            org_id=org_id,
            scope=scope_key,
            project_name=project_name,
            limit=self.max_context,
        )
        if not logs:
            return "No Hive Mind history found for that scope."

        context_lines = []
        for doc in logs:
            timestamp = doc.get("timestamp")
            if hasattr(timestamp, "isoformat"):
                ts_text = timestamp.isoformat()
            else:
                ts_text = str(timestamp)
            context_lines.append(
                f"- {ts_text} | {doc.get('user_display', doc.get('user_id', 'unknown'))} | "
                f"{doc.get('project_name', 'Unknown Project')} | {doc.get('summary', doc.get('task', ''))}"
            )

        context_blob = "\n".join(context_lines)
        prompt = (
            f"Question:\n{question}\n\n"
            f"Context from Hive Mind (latest first):\n{context_blob}\n\n"
            "Provide a concise answer with specific names/projects. "
            "If context is insufficient, reply with 'INSUFFICIENT CONTEXT'."
        )

        try:
            response = self.model.call_model(
                user_prompt=prompt,
                system_prompt="You are DevScope Oracle, summarizing engineering activity logs.",
            )
            reply = response.strip() if response else ""
            return reply or "Oracle could not generate a response."
        except Exception as exc:  # pragma: no cover - model errors
            logger.exception("Oracle generation failed: %s", exc)
            return f"Oracle error: {exc}"



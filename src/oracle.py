import logging
from typing import Optional

from api_models import create_model
from db import HiveMindClient

logger = logging.getLogger(__name__)


class OracleService:
    """Natural-language QA over the Hive Mind activity logs + summaries."""

    def __init__(
        self,
        hivemind: HiveMindClient,
        model_name: str = "gemini-2.0-flash",
        max_context: int = 40,
    ) -> None:
        self.hivemind = hivemind
        self.model = create_model(model_name)
        self.max_context = max_context

    def ask(self, question: str, org_id: Optional[str], project_name: Optional[str] = None) -> str:
        question = question.strip()
        if not question:
            return "Please enter a question for the Oracle."

        if not self.hivemind or not self.hivemind.enabled:
            return "Hive Mind is not configured. Set HIVEMIND_MONGO_URI to enable Oracle."

        if not org_id:
            return "Set your Organization ID in Settings to query the Hive Mind."

        scope_key = "project" if project_name else "org"
        logs = self.hivemind.query_activity(
            org_id=org_id,
            scope=scope_key,
            project_name=project_name,
            limit=self.max_context,
        )
        summaries = self.hivemind.query_summaries(org_id=org_id, limit=5)

        if not logs and not summaries:
            return "No Hive Mind history found for that scope."

        context_blob = self._format_context_blocks(logs, summaries)
        prompt = (
            f"Question:\n{question}\n\n"
            f"{context_blob}\n\n"
            "Provide a concise answer with specific names/projects."
        )

        try:
            response = self.model.call_model(
                user_prompt=prompt,
                system_prompt=(
                    "You are the Team Intelligence Engine. Use the Summaries for high-level context "
                    "and Raw Logs for specific details. Answer the user's question based STRICTLY on "
                    "this data. Do not hallucinate."
                ),
            )
            reply = response.strip() if response else ""
            return reply or "Oracle could not generate a response."
        except Exception as exc:  # pragma: no cover - model errors
            logger.exception("Oracle generation failed: %s", exc)
            return f"Oracle error: {exc}"

    @staticmethod
    def _format_context_blocks(logs, summaries) -> str:
        summary_lines = []
        for doc in summaries or []:
            ts_text = _safe_timestamp(doc.get("timestamp"))
            owner = doc.get("user_display") or doc.get("user_id", "unknown")
            summary_text = doc.get("summary_text", "").strip()
            summary_lines.append(f"[{owner} - {ts_text}] {summary_text}")

        log_lines = []
        for doc in logs or []:
            ts_text = _safe_timestamp(doc.get("timestamp"))
            owner = doc.get("user_display", doc.get("user_id", "unknown"))
            project = doc.get("project_name", "Unknown Project")
            detail = doc.get("summary") or doc.get("task", "")
            log_lines.append(f"[{owner} - {ts_text}] ({project}) {detail}")

        sections = []
        if summary_lines:
            sections.append("--- RECENT SESSION SUMMARIES (High Level) ---\n" + "\n".join(summary_lines))
        if log_lines:
            sections.append("--- RAW ACTIVITY LOGS (Low Level Details) ---\n" + "\n".join(log_lines))

        return "\n\n".join(sections) if sections else "No context available."


def _safe_timestamp(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value or "unknown time")



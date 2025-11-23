import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from api_models import create_model
from db import HiveMindClient

logger = logging.getLogger(__name__)

SECTION_ORDER = ("Summary", "People", "Risks", "Follow-Ups")


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

    def ask(
        self,
        question: str,
        *,
        org_id: Optional[str],
        scope: str = "org",
        project_name: Optional[str] = None,
        time_window_hours: Optional[int] = None,
    ) -> Dict[str, object]:
        question = question.strip()
        if not question:
            return self._empty_payload("Please enter a question for the Oracle.", question, scope, project_name, time_window_hours)

        if not self.hivemind or not self.hivemind.enabled:
            return self._empty_payload(
                "Hive Mind is not configured. Set HIVEMIND_MONGO_URI to enable Oracle.",
                question,
                scope,
                project_name,
                time_window_hours,
            )

        since = None
        if time_window_hours and time_window_hours > 0:
            since = datetime.utcnow() - timedelta(hours=time_window_hours)

        try:
            logs = self.hivemind.query_activity(
                org_id=org_id,
                scope=scope,
                project_name=project_name,
                limit=self.max_context,
                since=since,
            )
            summaries = self.hivemind.query_summaries(org_id=org_id, limit=5)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Hive Mind query failed: %s", exc)
            return self._empty_payload(f"Oracle error while reading Hive Mind: {exc}", question, scope, project_name, time_window_hours)

        ranked_logs = self._rank_logs(logs)
        context_blob, preview = self._format_context_blocks(ranked_logs, summaries)

        if not context_blob.strip():
            return self._empty_payload("No Hive Mind history found for that scope.", question, scope, project_name, time_window_hours)

        user_prompt = self._build_user_prompt(question, context_blob)
        system_prompt = self._build_system_prompt(scope, project_name, time_window_hours)

        try:
            response = self.model.call_model(user_prompt=user_prompt, system_prompt=system_prompt)
            reply = response.strip() if response else ""
        except Exception as exc:  # pragma: no cover - model errors
            logger.exception("Oracle generation failed: %s", exc)
            return self._empty_payload(f"Oracle error: {exc}", question, scope, project_name, time_window_hours)

        answer = reply or "Oracle could not generate a response."
        return {
            "question": question,
            "answer": answer,
            "scope": scope,
            "project_name": project_name,
            "time_window_hours": time_window_hours,
            "log_count": len(ranked_logs),
            "summary_count": len(summaries or []),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "context_preview": preview,
        }

    def _empty_payload(
        self,
        message: str,
        question: str,
        scope: str,
        project_name: Optional[str],
        time_window_hours: Optional[int],
    ) -> Dict[str, object]:
        return {
            "question": question,
            "answer": message,
            "scope": scope,
            "project_name": project_name,
            "time_window_hours": time_window_hours,
            "log_count": 0,
            "summary_count": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "context_preview": [],
        }

    def _rank_logs(self, logs: Sequence[Dict]) -> List[Dict]:
        seen: set = set()
        ranked: List[Dict] = []
        for doc in sorted(logs or [], key=lambda item: item.get("timestamp"), reverse=True):
            key = doc.get("summary") or doc.get("task") or doc.get("technical_context")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            ranked.append(doc)
            if len(ranked) >= self.max_context:
                break
        return ranked

    def _build_user_prompt(self, question: str, context_blob: str) -> str:
        return (
            "Team Question:\n"
            f"{question}\n\n"
            "Context from the DevScope Hive Mind:\n"
            f"{context_blob}\n\n"
            "Compose the response now."
        )

    def _build_system_prompt(self, scope: str, project_name: Optional[str], window: Optional[int]) -> str:
        scope_text = "organization-wide" if scope != "project" else f"project: {project_name}"
        window_text = f"last {window} hours" if window else "available history"
        sections = "\n".join(f"- {name}: bullet list of relevant items" for name in SECTION_ORDER)
        return (
            "You are DevScope's Team Oracle, an internal intelligence assistant.\n"
            f"- Scope: {scope_text}\n"
            f"- Time window: {window_text}\n\n"
            "CRITICAL: Always answer the question directly and concisely FIRST, before any structured sections.\n"
            "If the question asks for a count, number, or specific fact, provide that answer immediately at the start.\n"
            "Make the direct answer clear and prominent.\n\n"
            "You are only allowed to answer using the provided logs and summaries.\n"
            "After the direct answer, format the detailed response as Markdown with the following sections:\n"
            f"{sections}\n\n"
            "Formatting rules (IMPORTANT):\n"
            "- Use ## for section headers (e.g., ## Summary, ## People)\n"
            "- Use - for bullet points when listing items\n"
            "- If a section has NO content, write '## SectionName: None' on ONE line (not as a list item)\n"
            "- If a section HAS content, list the items with - bullets and DO NOT include 'None' in the list\n"
            "- Never include 'None' as a list item if there are actual items in that section\n"
            "- If a section would only contain 'None', you may skip it entirely if it adds no value\n"
            "- Always cite concrete names, repos, or tasks pulled from the context\n"
            "- Avoid redundant 'None' entries - one per empty section is enough\n\n"
            "Write naturally and conversationally. The direct answer should feel like a human response, not a template.\n\n"
            "Example good format:\n"
            "There are 3 people active in the organization: Charlie Kim, Eve Johnson, and Diana Patel.\n\n"
            "## Summary\n"
            "The team has been working on authentication improvements and resolving database deadlock issues.\n\n"
            "## People\n"
            "- Charlie Kim - Working on JWT authentication\n"
            "- Eve Johnson - Debugging async/await race conditions\n"
            "- Diana Patel - Resolving database deadlock issues\n\n"
            "## Risks: None\n\n"
            "## Follow-Ups: None\n\n"
            "Remember: Be natural, concise, and helpful. The direct answer should directly address what was asked."
        )

    def _format_context_blocks(
        self,
        logs: Sequence[Dict],
        summaries: Sequence[Dict],
    ) -> Tuple[str, List[str]]:
        summary_lines: List[str] = []
        for doc in summaries or []:
            ts_text = _safe_timestamp(doc.get("timestamp"))
            owner = doc.get("user_display") or doc.get("user_id", "unknown")
            summary_text = (doc.get("summary_text") or "").strip()
            if summary_text:
                summary_lines.append(f"[{owner} - {ts_text}] {summary_text}")

        log_lines: List[str] = []
        preview: List[str] = []
        for doc in logs or []:
            ts_text = _safe_timestamp(doc.get("timestamp"))
            owner = doc.get("user_display", doc.get("user_id", "unknown"))
            project = doc.get("project_name", "Unknown Project")
            detail = doc.get("summary") or doc.get("task") or doc.get("technical_context", "")
            line = f"[{owner} - {ts_text}] ({project}) {detail}"
            log_lines.append(line)
            if len(preview) < 4:
                preview.append(line)

        sections = []
        if summary_lines:
            sections.append("--- RECENT SESSION SUMMARIES (High Level) ---\n" + "\n".join(summary_lines))
        if log_lines:
            sections.append("--- RAW ACTIVITY LOGS (Low Level Details) ---\n" + "\n".join(log_lines))

        return ("\n\n".join(sections) if sections else ""), preview


def _safe_timestamp(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value or "unknown time")



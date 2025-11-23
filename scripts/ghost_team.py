#!/usr/bin/env python3
"""Seed Mongo Atlas with demo Hive Mind activity."""

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from constants import DEFAULT_ORG_ID  # noqa: E402
from db import HiveMindClient  # noqa: E402

PERSONAS: List[Dict] = [
    {
        "user_id": "alice",
        "user_display": "Alice – Frontend",
        "project_name": "Frontend-Experience",
        "session_goal": "Polish onboarding flow",
        "entries": [
            ("CODING", "Refining onboarding modal animations", "React, Framer Motion in auth_modal.tsx", "VS Code"),
            ("DESIGN", "Reviewing component spacing in Figma", "Figma board: Frontend UX refresh", "Figma"),
            ("DEBUGGING", "Fixing CSS bleed between dark/light themes", "theme.css variables audit", "VS Code"),
            ("RESEARCHING", "Checking Chakra UI docs for responsive Grid", "chakra-ui.com Grid docs", "Safari"),
        ],
    },
    {
        "user_id": "bob",
        "user_display": "Bob – DevOps",
        "project_name": "Platform-Infra",
        "session_goal": "Stabilize payments infra",
        "entries": [
            ("DEBUGGING", "Investigating 500s in payments ECS task", "CloudWatch logs for service/payments", "AWS Console"),
            ("CODING", "Updating Terraform module for RDS storage autoscale", "terraform/rds/main.tf adjustments", "VS Code"),
            ("RESEARCHING", "Reading Docker docs for build cache mounts", "docs.docker.com/build/cache", "Chrome"),
            ("MONITORING", "Watching ECS deployment rollout", "AWS Console deploy events", "AWS Console"),
        ],
    },
]


def build_payload(
    org_id: str,
    persona: Dict,
    entry: tuple,
    minutes_offset: int,
) -> Dict:
    timestamp = datetime.utcnow() - timedelta(minutes=minutes_offset)
    activity_type, summary, technical_context, app_name = entry
    return {
        "timestamp": timestamp,
        "session_id": f"ghost-{persona['user_id']}",
        "project_name": persona["project_name"],
        "session_goal": persona["session_goal"],
        "repo_path": f"/demo/{persona['project_name'].lower()}",
        "user_id": persona["user_id"],
        "user_display": persona["user_display"],
        "org_id": org_id,
        "summary": f"{summary} | {technical_context}",
        "task": summary,
        "activity_type": activity_type,
        "technical_context": technical_context,
        "app_name": app_name,
        "active_app": app_name,
        "window_title": summary,
        "alignment_score": random.randint(70, 95),
        "is_deep_work": True,
        "deep_work_state": "deep_work",
        "privacy_state": "allowed",
        "source": "ghost-team",
    }


def seed_persona(client: HiveMindClient, persona: Dict, org_id: str, entries: int) -> int:
    count = 0
    samples = persona["entries"]
    for idx in range(entries):
        entry = samples[idx % len(samples)]
        minutes_offset = random.randint(5, 300) + idx * 2
        payload = build_payload(org_id, persona, entry, minutes_offset)
        if client.publish_activity(payload):
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Hive Mind with ghost team data.")
    parser.add_argument("--org-id", default=DEFAULT_ORG_ID, help="Organization ID label")
    parser.add_argument("--entries", type=int, default=6, help="Entries per persona")
    args = parser.parse_args()

    client = HiveMindClient()
    if not client.enabled:
        print("Hive Mind is not configured. Set HIVEMIND_MONGO_URI before running the ghost generator.")
        sys.exit(1)

    total = 0
    for persona in PERSONAS:
        inserted = seed_persona(client, persona, args.org_id, args.entries)
        total += inserted
        print(f"Inserted {inserted} entries for {persona['user_display']}")

    print(f"Ghost team seeding complete. Total entries: {total}")


if __name__ == "__main__":
    main()



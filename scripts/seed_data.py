#!/usr/bin/env python3
"""Populate MongoDB Atlas with synthetic Hive Mind activity for demo purposes."""

import argparse
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from db import HiveMindClient  # noqa: E402

FRONTEND_EVENTS: List[Tuple[str, str, str, str]] = [
    ("CODING", "Polishing onboarding hero animation", "React component Hero.tsx", "VS Code"),
    ("DEBUGGING", "Fixing hydration mismatch warning", "Next.js console log", "Chrome DevTools"),
    ("RESEARCHING", "Reading Chakra UI responsive grid docs", "chakra-ui.com/Grid", "Safari"),
    ("CODING", "Tweaking tailwind config for dark mode", "tailwind.config.ts", "VS Code"),
    ("DESIGN", "Reviewing Figma frame 'Checkout Modal'", "Figma project – Growth", "Figma"),
]

DEVOPS_EVENTS: List[Tuple[str, str, str, str]] = [
    ("DEBUGGING", "Investigating ECS crash looping task payments-api", "CloudWatch logs group payments", "AWS Console"),
    ("CODING", "Updating Terraform module for RDS storage autoscale", "terraform/rds/main.tf", "VS Code"),
    ("RESEARCHING", "Reading Docker build cache mounts doc", "docs.docker.com/build/cache", "Chrome"),
    ("MONITORING", "Watching ArgoCD rollout for gateway", "ArgoCD dashboard", "Firefox"),
    ("CODING", "Patching GitHub Actions workflow for canary deploy", ".github/workflows/deploy.yaml", "VS Code"),
]


def build_payload(
    org_id: str,
    persona: Dict[str, str],
    entry: Tuple[str, str, str, str],
    minutes_offset: int,
) -> Dict:
    timestamp = datetime.utcnow() - timedelta(minutes=minutes_offset)
    task, summary, technical_context, app_name = entry
    return {
        "timestamp": timestamp,
        "session_id": f"seed-{persona['user_id']}",
        "project_name": persona["project_name"],
        "session_goal": persona["session_goal"],
        "repo_path": persona["repo_path"],
        "user_id": persona["user_id"],
        "user_display": persona["user_display"],
        "org_id": org_id,
        "summary": summary,
        "task": task,
        "technical_context": technical_context,
        "app_name": app_name,
        "active_app": app_name,
        "window_title": summary,
        "alignment_score": random.randint(70, 95),
        "is_deep_work": True,
        "source": "seed-data",
    }


def seed_persona(
    client: HiveMindClient,
    org_id: str,
    persona: Dict[str, str],
    templates: List[Tuple[str, str, str, str]],
) -> int:
    count = 0
    for idx in range(20):
        entry = templates[idx % len(templates)]
        minutes_offset = random.randint(5, 600) + idx * 3
        payload = build_payload(org_id, persona, entry, minutes_offset)
        if client.publish_activity(payload):
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fake team activity for the Hive Mind.")
    parser.add_argument("--org-id", default=os.environ.get("HIVEMIND_ORG_ID", "NYU-Team"), help="Organization ID label")
    args = parser.parse_args()

    client = HiveMindClient()
    if not client.enabled:
        print("Hive Mind is not configured. Set HIVEMIND_MONGO_URI before running the seeder.")
        sys.exit(1)

    personas = [
        {
            "user_id": "alice",
            "user_display": "Alice – Frontend",
            "project_name": "Frontend-Web",
            "session_goal": "Ship onboarding polish",
            "repo_path": "/demo/frontend",
        },
        {
            "user_id": "bob",
            "user_display": "Bob – DevOps",
            "project_name": "Platform-Infra",
            "session_goal": "Stabilize payments infra",
            "repo_path": "/demo/infra",
        },
    ]

    total = 0
    total += seed_persona(client, args.org_id, personas[0], FRONTEND_EVENTS)
    total += seed_persona(client, args.org_id, personas[1], DEVOPS_EVENTS)
    print(f"Inserted {total} synthetic entries into the Hive Mind for org '{args.org_id}'.")


if __name__ == "__main__":
    main()


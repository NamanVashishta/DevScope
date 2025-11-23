#!/usr/bin/env python3
"""Enhanced seed data generator for DevScope Hive Mind.

Generates realistic activity logs and session summaries matching the ActivityRecord schema.
Supports 500-1000+ entries across 30 days for 5-8 team members.
"""

import argparse
import random
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from constants import DEFAULT_ORG_ID  # noqa: E402
from db import HiveMindClient  # noqa: E402

# Activity type constants
ACTIVITY_TYPES = [
    "CODING",
    "DEBUGGING",
    "RESEARCHING",
    "REVIEWING",
    "TESTING",
    "COMMUNICATING",
    "DESIGN",
    "MONITORING",
    "DEPLOYING",
]

# Realistic error codes
ERROR_CODES = [
    "HTTP 400",
    "HTTP 404",
    "HTTP 409",
    "HTTP 500",
    "HTTP 502",
    "HTTP 503",
    "TypeError",
    "ValueError",
    "AttributeError",
    "KeyError",
    "NullReferenceException",
    "ECONNREFUSED",
    "ETIMEDOUT",
    "ENOTFOUND",
]

# Documentation URLs by domain
DOC_URLS = {
    "react": [
        ("React Hooks Documentation", "https://react.dev/reference/react"),
        ("React Router v6 Guide", "https://reactrouter.com/en/main"),
        ("React Testing Library", "https://testing-library.com/react"),
    ],
    "python": [
        ("Python Async/Await", "https://docs.python.org/3/library/asyncio.html"),
        ("FastAPI Documentation", "https://fastapi.tiangolo.com/"),
        ("Pydantic Models", "https://docs.pydantic.dev/"),
    ],
    "aws": [
        ("AWS ECS Best Practices", "https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/"),
        ("AWS Lambda Configuration", "https://docs.aws.amazon.com/lambda/"),
        ("Terraform AWS Provider", "https://registry.terraform.io/providers/hashicorp/aws/latest/docs"),
    ],
    "docker": [
        ("Docker Build Cache", "https://docs.docker.com/build/cache/"),
        ("Docker Compose Networking", "https://docs.docker.com/compose/networking/"),
    ],
    "stripe": [
        ("Stripe API - Idempotency Keys", "https://stripe.com/docs/api/idempotent_requests"),
        ("Stripe Webhooks Guide", "https://stripe.com/docs/webhooks"),
    ],
    "general": [
        ("MDN Web Docs", "https://developer.mozilla.org/"),
        ("Stack Overflow", "https://stackoverflow.com/"),
        ("GitHub Documentation", "https://docs.github.com/"),
    ],
}

# Realistic window titles by app
WINDOW_TITLES = {
    "VS Code": [
        "monitor.py — VS Code",
        "webhook_handler.py — VS Code",
        "App.tsx — VS Code",
        "package.json — VS Code",
        "docker-compose.yml — VS Code",
        "test_utils.py — VS Code",
        "schema.sql — VS Code",
    ],
    "WebStorm": [
        "App.tsx — WebStorm",
        "index.ts — WebStorm",
        "package.json — WebStorm",
    ],
    "PyCharm": [
        "monitor.py — PyCharm",
        "db.py — PyCharm",
        "test_monitor.py — PyCharm",
    ],
    "Xcode": [
        "AppDelegate.swift — Xcode",
        "ContentView.swift — Xcode",
    ],
    "Chrome": [
        "React Documentation - Chrome",
        "AWS Console - Chrome",
        "Stack Overflow - Chrome",
    ],
    "Safari": [
        "Stripe API Docs - Safari",
        "Docker Documentation - Safari",
    ],
}

# Focus bounds (x, y, width, height) - realistic screen coordinates
FOCUS_BOUNDS_OPTIONS = [
    (100, 200, 1200, 800),
    (150, 150, 1400, 900),
    (200, 100, 1600, 1000),
    (50, 250, 1100, 750),
]


def _slugify(value: str) -> str:
    """Convert project name to slug."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "project"


class Persona:
    """Represents a team member with their role, projects, and activity patterns."""

    def __init__(
        self,
        user_id: str,
        user_display: str,
        role: str,
        projects: List[Dict],
        activity_patterns: List[Dict],
    ):
        self.user_id = user_id
        self.user_display = user_display
        self.role = role
        self.projects = projects
        self.activity_patterns = activity_patterns

    def get_random_project(self) -> Dict:
        """Get a random project for this persona."""
        return random.choice(self.projects)

    def get_random_activity_pattern(self) -> Dict:
        """Get a random activity pattern."""
        return random.choice(self.activity_patterns)


# Define comprehensive personas
PERSONAS = [
    Persona(
        user_id="alice",
        user_display="Alice Chen",
        role="Frontend Engineer",
        projects=[
            {
                "project_name": "Frontend-Experience",
                "repo_path": "/Users/alice/dev/frontend-experience",
                "session_goals": [
                    "Polish onboarding flow",
                    "Implement dark mode toggle",
                    "Fix responsive layout issues",
                    "Add accessibility features",
                    "Optimize bundle size",
                ],
            },
            {
                "project_name": "Mobile-App",
                "repo_path": "/Users/alice/dev/mobile-app",
                "session_goals": [
                    "Fix navigation bugs",
                    "Implement push notifications",
                    "Optimize image loading",
                ],
            },
        ],
        activity_patterns=[
            {
                "activity_type": "CODING",
                "app_name": "VS Code",
                "tasks": [
                    "Refining onboarding modal animations",
                    "Implementing dark mode theme switcher",
                    "Adding responsive breakpoints",
                    "Creating reusable button component",
                ],
                "technical_contexts": [
                    "React, Framer Motion in auth_modal.tsx",
                    "theme.css variables and CSS custom properties",
                    "Tailwind CSS responsive utilities",
                    "TypeScript component props interface",
                ],
                "function_targets": [
                    "auth_modal.tsx > OnboardingModal",
                    "theme.ts > toggleDarkMode()",
                    "Button.tsx > Button component",
                ],
                "doc_domain": "react",
            },
            {
                "activity_type": "DEBUGGING",
                "app_name": "VS Code",
                "tasks": [
                    "Fixing CSS bleed between dark/light themes",
                    "Resolving TypeScript type errors",
                    "Debugging React re-render loop",
                ],
                "technical_contexts": [
                    "theme.css variables audit",
                    "TypeScript strict mode type checking",
                    "React DevTools profiler analysis",
                ],
                "function_targets": [
                    "theme.css > :root variables",
                    "App.tsx > useEffect dependencies",
                ],
                "error_codes": ["TypeError", "KeyError"],
                "doc_domain": "react",
            },
            {
                "activity_type": "RESEARCHING",
                "app_name": "Chrome",
                "tasks": [
                    "Checking Chakra UI docs for responsive Grid",
                    "Reading React Router v6 migration guide",
                    "Reviewing accessibility best practices",
                ],
                "technical_contexts": [
                    "chakra-ui.com Grid docs",
                    "reactrouter.com migration guide",
                    "MDN ARIA attributes",
                ],
                "doc_domain": "react",
            },
        ],
    ),
    Persona(
        user_id="bob",
        user_display="Bob Martinez",
        role="DevOps Engineer",
        projects=[
            {
                "project_name": "Platform-Infra",
                "repo_path": "/Users/bob/dev/platform-infra",
                "session_goals": [
                    "Stabilize payments infra",
                    "Set up CI/CD pipeline",
                    "Optimize ECS task scaling",
                    "Implement monitoring dashboards",
                ],
            },
        ],
        activity_patterns=[
            {
                "activity_type": "DEBUGGING",
                "app_name": "AWS Console",
                "tasks": [
                    "Investigating 500s in payments ECS task",
                    "Analyzing CloudWatch log errors",
                    "Troubleshooting RDS connection timeouts",
                ],
                "technical_contexts": [
                    "CloudWatch logs for service/payments",
                    "ECS task definition health checks",
                    "RDS connection pool configuration",
                ],
                "function_targets": [
                    "terraform/ecs/main.tf > task_definition",
                    "docker-compose.yml > services.payments",
                ],
                "error_codes": ["HTTP 500", "HTTP 502", "ETIMEDOUT"],
                "doc_domain": "aws",
            },
            {
                "activity_type": "CODING",
                "app_name": "VS Code",
                "tasks": [
                    "Updating Terraform module for RDS storage autoscale",
                    "Writing CloudFormation templates",
                    "Configuring GitHub Actions workflows",
                ],
                "technical_contexts": [
                    "terraform/rds/main.tf adjustments",
                    "cloudformation/ecs-cluster.yml",
                    ".github/workflows/deploy.yml",
                ],
                "function_targets": [
                    "terraform/rds/main.tf > aws_db_instance",
                    ".github/workflows/deploy.yml > deploy job",
                ],
                "doc_domain": "aws",
            },
            {
                "activity_type": "MONITORING",
                "app_name": "AWS Console",
                "tasks": [
                    "Watching ECS deployment rollout",
                    "Monitoring CloudWatch metrics",
                    "Reviewing cost optimization reports",
                ],
                "technical_contexts": [
                    "AWS Console deploy events",
                    "CloudWatch dashboard for API latency",
                ],
                "doc_domain": "aws",
            },
        ],
    ),
    Persona(
        user_id="charlie",
        user_display="Charlie Kim",
        role="Backend Engineer",
        projects=[
            {
                "project_name": "Payments-API",
                "repo_path": "/Users/charlie/dev/payments-api",
                "session_goals": [
                    "Fix Stripe webhook retries",
                    "Implement rate limiting",
                    "Add API authentication",
                    "Optimize database queries",
                ],
            },
            {
                "project_name": "User-Service",
                "repo_path": "/Users/charlie/dev/user-service",
                "session_goals": [
                    "Implement user profile endpoints",
                    "Add email verification",
                    "Fix session management bugs",
                ],
            },
        ],
        activity_patterns=[
            {
                "activity_type": "DEBUGGING",
                "app_name": "VS Code",
                "tasks": [
                    "Fixing HTTP 409 error in webhook handler",
                    "Resolving database deadlock issues",
                    "Debugging async/await race conditions",
                ],
                "technical_contexts": [
                    "webhook_handler.py > process_webhook() | Stripe idempotency key conflict",
                    "db.py > transaction isolation level",
                    "async_utils.py > concurrent task handling",
                ],
                "function_targets": [
                    "webhook_handler.py > process_webhook()",
                    "db.py > execute_transaction()",
                    "async_utils.py > run_concurrent()",
                ],
                "error_codes": ["HTTP 409", "HTTP 500", "AttributeError"],
                "doc_domain": "stripe",
            },
            {
                "activity_type": "CODING",
                "app_name": "PyCharm",
                "tasks": [
                    "Implementing rate limiter middleware",
                    "Adding JWT authentication",
                    "Writing database migration scripts",
                ],
                "technical_contexts": [
                    "middleware/rate_limiter.py using Redis",
                    "auth/jwt_handler.py",
                    "migrations/001_add_user_table.sql",
                ],
                "function_targets": [
                    "middleware/rate_limiter.py > RateLimiter",
                    "auth/jwt_handler.py > generate_token()",
                ],
                "doc_domain": "python",
            },
            {
                "activity_type": "RESEARCHING",
                "app_name": "Chrome",
                "tasks": [
                    "Reading FastAPI async best practices",
                    "Reviewing Stripe webhook documentation",
                    "Checking Redis connection pooling",
                ],
                "technical_contexts": [
                    "fastapi.tiangolo.com async patterns",
                    "stripe.com/docs/webhooks",
                ],
                "doc_domain": "stripe",
            },
        ],
    ),
    Persona(
        user_id="diana",
        user_display="Diana Patel",
        role="Mobile Developer",
        projects=[
            {
                "project_name": "Mobile-App",
                "repo_path": "/Users/diana/dev/mobile-app",
                "session_goals": [
                    "Fix navigation stack issues",
                    "Implement offline mode",
                    "Add biometric authentication",
                    "Optimize app startup time",
                ],
            },
        ],
        activity_patterns=[
            {
                "activity_type": "CODING",
                "app_name": "Xcode",
                "tasks": [
                    "Implementing navigation stack",
                    "Adding offline data sync",
                    "Creating biometric auth flow",
                ],
                "technical_contexts": [
                    "NavigationStack.swift > navigation logic",
                    "OfflineManager.swift > local storage",
                    "BiometricAuth.swift > Face ID integration",
                ],
                "function_targets": [
                    "NavigationStack.swift > pushViewController()",
                    "OfflineManager.swift > syncData()",
                    "BiometricAuth.swift > authenticate()",
                ],
                "doc_domain": "general",
            },
            {
                "activity_type": "DEBUGGING",
                "app_name": "Xcode",
                "tasks": [
                    "Fixing memory leaks in image cache",
                    "Resolving navigation back button issues",
                    "Debugging crash on app launch",
                ],
                "technical_contexts": [
                    "ImageCache.swift > memory management",
                    "NavigationController.swift > back navigation",
                    "AppDelegate.swift > launch sequence",
                ],
                "function_targets": [
                    "ImageCache.swift > clearCache()",
                    "NavigationController.swift > popViewController()",
                ],
                "error_codes": ["NullReferenceException"],
                "doc_domain": "general",
            },
        ],
    ),
    Persona(
        user_id="eve",
        user_display="Eve Johnson",
        role="Data Engineer",
        projects=[
            {
                "project_name": "Analytics-Pipeline",
                "repo_path": "/Users/eve/dev/analytics-pipeline",
                "session_goals": [
                    "Optimize ETL job performance",
                    "Fix data quality issues",
                    "Implement real-time streaming",
                    "Add data validation rules",
                ],
            },
        ],
        activity_patterns=[
            {
                "activity_type": "CODING",
                "app_name": "VS Code",
                "tasks": [
                    "Writing Spark transformation jobs",
                    "Creating data validation schemas",
                    "Implementing Kafka consumers",
                ],
                "technical_contexts": [
                    "spark_jobs/transform.py > DataFrame operations",
                    "schemas/validation.py > Pydantic models",
                    "kafka/consumer.py > message processing",
                ],
                "function_targets": [
                    "transform.py > process_batch()",
                    "validation.py > validate_schema()",
                    "consumer.py > consume_messages()",
                ],
                "doc_domain": "python",
            },
            {
                "activity_type": "DEBUGGING",
                "app_name": "VS Code",
                "tasks": [
                    "Fixing data type mismatches",
                    "Resolving memory issues in Spark",
                    "Debugging Kafka lag",
                ],
                "technical_contexts": [
                    "transform.py > type conversion errors",
                    "spark_config.py > executor memory settings",
                    "kafka_monitor.py > consumer lag metrics",
                ],
                "function_targets": [
                    "transform.py > cast_types()",
                    "spark_config.py > configure_executors()",
                ],
                "error_codes": ["TypeError", "ValueError"],
                "doc_domain": "python",
            },
        ],
    ),
    Persona(
        user_id="frank",
        user_display="Frank Williams",
        role="Full-stack Developer",
        projects=[
            {
                "project_name": "E-Commerce-Platform",
                "repo_path": "/Users/frank/dev/ecommerce-platform",
                "session_goals": [
                    "Implement checkout flow",
                    "Add product search",
                    "Fix payment processing bugs",
                    "Optimize database queries",
                ],
            },
        ],
        activity_patterns=[
            {
                "activity_type": "CODING",
                "app_name": "WebStorm",
                "tasks": [
                    "Building checkout component",
                    "Implementing search API",
                    "Writing database queries",
                ],
                "technical_contexts": [
                    "components/Checkout.tsx > payment form",
                    "api/search.ts > Elasticsearch integration",
                    "queries/products.sql > JOIN optimization",
                ],
                "function_targets": [
                    "Checkout.tsx > handlePayment()",
                    "search.ts > searchProducts()",
                    "products.sql > getProductsWithInventory()",
                ],
                "doc_domain": "react",
            },
            {
                "activity_type": "DEBUGGING",
                "app_name": "WebStorm",
                "tasks": [
                    "Fixing payment gateway timeout",
                    "Resolving search index issues",
                    "Debugging cart persistence",
                ],
                "technical_contexts": [
                    "payment_gateway.ts > timeout handling",
                    "search_index.py > index update logic",
                    "cart_service.ts > localStorage sync",
                ],
                "function_targets": [
                    "payment_gateway.ts > processPayment()",
                    "search_index.py > updateIndex()",
                ],
                "error_codes": ["HTTP 504", "ETIMEDOUT"],
                "doc_domain": "general",
            },
        ],
    ),
    Persona(
        user_id="grace",
        user_display="Grace Lee",
        role="QA Engineer",
        projects=[
            {
                "project_name": "Test-Automation",
                "repo_path": "/Users/grace/dev/test-automation",
                "session_goals": [
                    "Write E2E tests for checkout",
                    "Fix flaky integration tests",
                    "Add performance test suite",
                    "Improve test coverage",
                ],
            },
        ],
        activity_patterns=[
            {
                "activity_type": "TESTING",
                "app_name": "VS Code",
                "tasks": [
                    "Writing Playwright E2E tests",
                    "Creating Jest unit tests",
                    "Setting up Cypress test suite",
                ],
                "technical_contexts": [
                    "e2e/checkout.spec.ts > Playwright test",
                    "unit/api.test.ts > Jest mocks",
                    "cypress/integration/auth.spec.js",
                ],
                "function_targets": [
                    "checkout.spec.ts > testCheckoutFlow()",
                    "api.test.ts > testPaymentEndpoint()",
                ],
                "doc_domain": "general",
            },
            {
                "activity_type": "DEBUGGING",
                "app_name": "VS Code",
                "tasks": [
                    "Fixing flaky test timeouts",
                    "Resolving test data cleanup issues",
                    "Debugging CI test failures",
                ],
                "technical_contexts": [
                    "test_utils.ts > timeout configuration",
                    "test_fixtures.py > database cleanup",
                    ".github/workflows/test.yml > CI config",
                ],
                "function_targets": [
                    "test_utils.ts > waitForElement()",
                    "test_fixtures.py > resetDatabase()",
                ],
                "error_codes": ["ETIMEDOUT"],
                "doc_domain": "general",
            },
        ],
    ),
]


def generate_realistic_timestamp(days_back: int, work_hours_only: bool = True) -> datetime:
    """Generate a realistic timestamp within the last N days."""
    now = datetime.utcnow()
    days_ago = random.randint(0, days_back)
    base_time = now - timedelta(days=days_ago)

    # Prefer weekdays (0=Monday, 6=Sunday)
    weekday = base_time.weekday()
    if weekday >= 5:  # Weekend
        # 30% chance of weekend work
        if random.random() > 0.3:
            # Move to nearest weekday
            days_adjust = 1 if weekday == 5 else -1
            base_time = base_time + timedelta(days=days_adjust)

    if work_hours_only:
        # Work hours: 9 AM to 6 PM (9:00 to 18:00)
        hour = random.randint(9, 17)
        minute = random.randint(0, 59)
        base_time = base_time.replace(hour=hour, minute=minute, second=random.randint(0, 59))
    else:
        # Some off-hours work (10% chance)
        if random.random() < 0.1:
            hour = random.choice([7, 8, 19, 20, 21])
            minute = random.randint(0, 59)
            base_time = base_time.replace(hour=hour, minute=minute, second=random.randint(0, 59))

    return base_time


def generate_activity_entry(
    persona: Persona,
    session_id: str,
    project: Dict,
    session_goal: str,
    timestamp: datetime,
    org_id: str,
) -> Dict:
    """Generate a single realistic activity entry."""
    pattern = persona.get_random_activity_pattern()
    task = random.choice(pattern["tasks"])
    technical_context = random.choice(pattern["technical_contexts"])

    # Generate function target if available
    function_target = None
    if "function_targets" in pattern:
        function_target = random.choice(pattern["function_targets"])

    # Generate error code if debugging/testing
    error_code = None
    if pattern["activity_type"] in ["DEBUGGING", "TESTING"] and "error_codes" in pattern:
        if random.random() < 0.7:  # 70% chance of having an error code
            error_code = random.choice(pattern["error_codes"])

    # Generate documentation info
    doc_title = None
    doc_url = None
    if pattern["activity_type"] == "RESEARCHING" or random.random() < 0.3:
        doc_domain = pattern.get("doc_domain", "general")
        if doc_domain in DOC_URLS:
            doc_title, doc_url = random.choice(DOC_URLS[doc_domain])

    # Generate window title
    app_name = pattern["app_name"]
    window_title = random.choice(WINDOW_TITLES.get(app_name, [f"{task} — {app_name}"]))

    # Generate focus bounds (70% chance)
    focus_bounds = None
    if random.random() < 0.7:
        focus_bounds = random.choice(FOCUS_BOUNDS_OPTIONS)

    # Determine work state
    is_deep_work = pattern["activity_type"] in ["CODING", "DEBUGGING", "TESTING"]
    if pattern["activity_type"] == "RESEARCHING":
        is_deep_work = random.random() < 0.8  # 80% of research is deep work
    elif pattern["activity_type"] == "COMMUNICATING":
        is_deep_work = False

    deep_work_state = "deep_work" if is_deep_work else "distracted"
    privacy_state = "allowed" if is_deep_work else ("blocked" if random.random() < 0.3 else "allowed")
    alignment_score = random.randint(75, 98) if is_deep_work else random.randint(40, 70)

    project_slug = _slugify(project["project_name"])

    payload = {
        "timestamp": timestamp,
        "session_id": session_id,
        "project_name": project["project_name"],
        "project_slug": project_slug,
        "session_goal": session_goal,
        "repo_path": project["repo_path"],
        "task": task,
        "activity_type": pattern["activity_type"],
        "technical_context": technical_context,
        "app_name": app_name,
        "active_app": app_name,
        "window_title": window_title,
        "alignment_score": alignment_score,
        "is_deep_work": is_deep_work,
        "deep_work_state": deep_work_state,
        "privacy_state": privacy_state,
        "user_id": persona.user_id,
        "user_display": persona.user_display,
        "org_id": org_id,
        "source": "ghost-team",
    }

    # Add optional fields
    if error_code:
        payload["error_code"] = error_code
    if function_target:
        payload["function_target"] = function_target
    if doc_title:
        payload["documentation_title"] = doc_title
    if doc_url:
        payload["doc_url"] = doc_url
    if focus_bounds:
        payload["focus_bounds"] = {"x": focus_bounds[0], "y": focus_bounds[1], "width": focus_bounds[2], "height": focus_bounds[3]}

    return payload


def generate_session_summary(
    session_id: str,
    persona: Persona,
    project: Dict,
    session_goal: str,
    activities: List[Dict],
    org_id: str,
) -> Dict:
    """Generate a realistic session summary matching batch.py format."""
    # Calculate time range
    if not activities:
        return None

    timestamps = [a["timestamp"] for a in activities]
    start_time = min(timestamps)
    end_time = max(timestamps)
    time_range_minutes = max(1, int((end_time - start_time).total_seconds() / 60))

    # Count activity types
    activity_counts = defaultdict(int)
    for activity in activities:
        activity_counts[activity["activity_type"]] += 1

    # Generate realistic summary text
    features = []
    bugs = []
    research = []

    for activity in activities:
        if activity["activity_type"] == "CODING":
            features.append(f"- {activity['task']} ({activity.get('function_target', 'N/A')})")
        elif activity["activity_type"] == "DEBUGGING":
            error = activity.get("error_code", "Unknown error")
            bugs.append(f"- {activity['task']} (Error: {error})")
        elif activity["activity_type"] == "RESEARCHING":
            doc = activity.get("documentation_title", "Documentation")
            research.append(f"- {doc}")

    # Build markdown summary
    summary_lines = [
        f"# Session Summary: {session_goal}",
        "",
        "## Features Implemented:",
    ]
    if features:
        summary_lines.extend(features[:5])  # Limit to 5
    else:
        summary_lines.append("None")

    summary_lines.extend(["", "## Bugs Debugged:"])
    if bugs:
        summary_lines.extend(bugs[:5])
    else:
        summary_lines.append("None")

    summary_lines.extend(["", "## Key Research:"])
    if research:
        summary_lines.extend(research[:5])
    else:
        summary_lines.append("None")

    # Calculate context score (0-10)
    deep_work_count = sum(1 for a in activities if a.get("is_deep_work", False))
    context_score = min(10, int((deep_work_count / len(activities)) * 10)) if activities else 5

    summary_lines.extend(["", f"## Context Score: {context_score}/10"])
    summary_text = "\n".join(summary_lines)

    return {
        "org_id": org_id,
        "user_id": persona.user_id,
        "session_id": session_id,
        "project_name": project["project_name"],
        "session_goal": session_goal,
        "repo_path": project["repo_path"],
        "timestamp": end_time,  # Summary timestamp is end of session
        "summary_text": summary_text,
        "time_range_minutes": time_range_minutes,
    }


def generate_session_activities(
    persona: Persona,
    project: Dict,
    session_goal: str,
    session_id: str,
    start_time: datetime,
    entries_per_session: int,
    org_id: str,
) -> List[Dict]:
    """Generate a sequence of activities for a single session."""
    activities = []
    current_time = start_time

    for i in range(entries_per_session):
        # Activities are typically 5-15 minutes apart
        minutes_offset = random.randint(5, 15)
        if i > 0:
            current_time = current_time + timedelta(minutes=minutes_offset)

        activity = generate_activity_entry(
            persona=persona,
            session_id=session_id,
            project=project,
            session_goal=session_goal,
            timestamp=current_time,
            org_id=org_id,
        )
        activities.append(activity)

    return activities


def seed_persona(
    client: HiveMindClient,
    persona: Persona,
    org_id: str,
    entries_per_user: int,
    days: int,
    include_summaries: bool,
) -> Tuple[int, int]:
    """Generate and insert activities and summaries for a persona."""
    activities_inserted = 0
    summaries_inserted = 0

    # Group activities into sessions
    # Each session has 5-20 activities
    entries_per_session = random.randint(5, 20)
    num_sessions = max(1, entries_per_user // entries_per_session)

    sessions_data = []

    for session_idx in range(num_sessions):
        project = persona.get_random_project()
        session_goal = random.choice(project["session_goals"])
        session_id = f"ghost-{persona.user_id}-{uuid.uuid4().hex[:8]}"

        # Generate start time for this session
        start_time = generate_realistic_timestamp(days, work_hours_only=True)

        # Generate activities for this session
        session_activities = generate_session_activities(
            persona=persona,
            project=project,
            session_goal=session_goal,
            session_id=session_id,
            start_time=start_time,
            entries_per_session=entries_per_session,
            org_id=org_id,
        )

        # Batch insert activities
        batch_size = 50
        for i in range(0, len(session_activities), batch_size):
            batch = session_activities[i : i + batch_size]
            for activity in batch:
                if client.publish_activity(activity):
                    activities_inserted += 1

        # Store session data for summary generation
        if include_summaries:
            sessions_data.append((session_id, persona, project, session_goal, session_activities))

    # Generate and insert summaries
    if include_summaries:
        for session_id, persona, project, session_goal, session_activities in sessions_data:
            summary = generate_session_summary(
                session_id=session_id,
                persona=persona,
                project=project,
                session_goal=session_goal,
                activities=session_activities,
                org_id=org_id,
            )
            if summary and client.save_summary(summary):
                summaries_inserted += 1

    return activities_inserted, summaries_inserted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate comprehensive seed data for DevScope Hive Mind.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--org-id",
        default=DEFAULT_ORG_ID,
        help=f"Organization ID (default: {DEFAULT_ORG_ID})",
    )
    parser.add_argument(
        "--entries-per-user",
        type=int,
        default=120,
        help="Number of activity entries per user (default: 120, total ~500-1000)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Time range in days (default: 30)",
    )
    parser.add_argument(
        "--include-summaries",
        action="store_true",
        default=True,
        help="Generate session summaries (default: True)",
    )
    parser.add_argument(
        "--no-summaries",
        dest="include_summaries",
        action="store_false",
        help="Skip session summary generation",
    )

    args = parser.parse_args()

    client = HiveMindClient()
    if not client.enabled:
        print("ERROR: Hive Mind is not configured.")
        print("Set HIVEMIND_MONGO_URI before running the seed generator.")
        sys.exit(1)

    print(f"Generating seed data for {len(PERSONAS)} team members...")
    print(f"  - Entries per user: {args.entries_per_user}")
    print(f"  - Time range: {args.days} days")
    print(f"  - Include summaries: {args.include_summaries}")
    print(f"  - Organization: {args.org_id}")
    print()

    total_activities = 0
    total_summaries = 0

    for persona in PERSONAS:
        print(f"Processing {persona.user_display} ({persona.role})...", end=" ", flush=True)
        activities, summaries = seed_persona(
            client=client,
            persona=persona,
            org_id=args.org_id,
            entries_per_user=args.entries_per_user,
            days=args.days,
            include_summaries=args.include_summaries,
        )
        total_activities += activities
        total_summaries += summaries
        print(f"✓ {activities} activities, {summaries} summaries")

    print()
    print("=" * 60)
    print(f"Seed data generation complete!")
    print(f"  - Total activities: {total_activities}")
    print(f"  - Total summaries: {total_summaries}")
    print(f"  - Total records: {total_activities + total_summaries}")
    print("=" * 60)


if __name__ == "__main__":
    main()

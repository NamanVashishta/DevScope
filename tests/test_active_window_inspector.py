import sys
import types
import unittest
from pathlib import Path
from unittest import mock


class _StubMSSContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    @property
    def monitors(self):
        return [{"left": 0, "top": 0, "width": 1, "height": 1}]

    def grab(self, monitor):
        raise RuntimeError("mss.grab should not be called in this test suite.")


class _StubMSSModule(types.SimpleNamespace):
    def mss(self):
        return _StubMSSContext()


sys.modules.setdefault("mss", _StubMSSModule())


class _StubGenAIModule(types.SimpleNamespace):
    def configure(self, **_: object) -> None:  # pragma: no cover - simple stub
        return None

    class GenerativeModel:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def generate_content(self, *_: object, **__: object):
            return types.SimpleNamespace(text="{}")

        def count_tokens(self, *_: object, **__: object):
            return types.SimpleNamespace(total_tokens=0)


sys.modules.setdefault("google.generativeai", _StubGenAIModule())

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import monitor


class ActiveWindowInspectorTests(unittest.TestCase):
    def test_snapshot_uses_cache_until_expired(self) -> None:
        inspector = monitor.ActiveWindowInspector()
        fake_snapshot = monitor.ActiveWindowSnapshot(app="VS Code", title="main.py", bounds=(1, 2, 3, 4))

        with mock.patch.object(inspector, "_fetch_snapshot", return_value=fake_snapshot) as fetch:
            first = inspector.snapshot(cache_max_age=0.0)
            second = inspector.snapshot()

        self.assertEqual(first, fake_snapshot)
        self.assertIs(first, second)
        fetch.assert_called_once()

    def test_format_focus_bounds_handles_none(self) -> None:
        formatted_unknown = monitor._format_focus_bounds(None)
        formatted_real = monitor._format_focus_bounds((10, 20, 300, 400))

        self.assertEqual(formatted_unknown, "Unknown")
        self.assertIn("x=10", formatted_real)
        self.assertIn("height=400", formatted_real)


if __name__ == "__main__":
    unittest.main()


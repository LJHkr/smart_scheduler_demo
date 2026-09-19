import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "deepseek_agent"))

from deepseek_app_v3 import add_automatic_explanation, run_explanation  # noqa: E402
from scheduler import generate_schedule  # noqa: E402


FAKE_EXPLANATION = {
    "answer": "该排班优先满足硬规则，再考虑偏好。",
    "key_reasons": [
        {"title": "技能覆盖", "detail": "每班覆盖关键技能。", "evidence": ["R-01～R-03"]}
    ],
    "tradeoffs": ["硬规则优先于偏好"],
    "limitations": [],
    "read_only_confirmation": True,
    "model": "deepseek-flash",
}


class ExplanationModeTests(unittest.TestCase):
    def setUp(self):
        self.base = generate_schedule("生成完整一周排班")
        self.assertTrue(self.base["success"])

    def test_explanation_requires_existing_schedule(self):
        result = run_explanation("为什么这样排？", [], {})
        self.assertFalse(result["success"])
        self.assertTrue(result["needs_base_schedule"])

    def test_question_does_not_change_schedule(self):
        before = copy.deepcopy(self.base["schedule"])
        with patch("deepseek_app_v3.explain_schedule", return_value=copy.deepcopy(FAKE_EXPLANATION)):
            result = run_explanation("为什么周三这样安排？", self.base["schedule"], self.base["request"])
        self.assertTrue(result["success"])
        self.assertTrue(result["schedule_unchanged"])
        self.assertEqual(before, self.base["schedule"])

    def test_successful_schedule_gets_automatic_explanation(self):
        with patch("deepseek_app_v3.explain_schedule", return_value=copy.deepcopy(FAKE_EXPLANATION)):
            result = add_automatic_explanation(copy.deepcopy(self.base), "请解释整体安排")
        self.assertIn("explanation", result)
        self.assertTrue(result["explanation"]["read_only_confirmation"])


if __name__ == "__main__":
    unittest.main()

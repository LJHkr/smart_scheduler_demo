import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "deepseek_agent"))

from deepseek_app import run_revision  # noqa: E402
from scheduler import generate_schedule  # noqa: E402


class AppendModeTests(unittest.TestCase):
    def setUp(self):
        self.base = generate_schedule("生成完整一周排班")
        self.assertTrue(self.base["success"])
        self.plain = [
            {"day": item["day"], "shift": item["shift"], "employees": item["employees"]}
            for item in self.base["schedule"]
        ]

    def test_append_requires_existing_schedule(self):
        result = run_revision("周三不安排E07", [], {})
        self.assertFalse(result["success"])
        self.assertTrue(result["needs_base_schedule"])

    def test_valid_revision_keeps_existing_table(self):
        revision = {
            "understanding": "当前排班已满足需求",
            "needs_clarification": False,
            "clarification_question": "",
            "requirement_satisfied": True,
            "requirement_evidence": "检查完成",
            "schedule": self.plain,
            "change_summary": [],
        }
        with patch("deepseek_app.revise_schedule", return_value=revision):
            result = run_revision("保持现有排班", self.base["schedule"], self.base["request"])
        self.assertTrue(result["success"])
        self.assertEqual(["现有排班已经满足追加需求，无需调整。"], result["changes"])

    def test_invalid_first_revision_is_retried(self):
        invalid = [dict(item) for item in self.plain]
        invalid[0] = {"day": invalid[0]["day"], "shift": invalid[0]["shift"], "employees": ["E06", "E07", "E08", "E12"]}
        first = {
            "understanding": "第一次修改",
            "needs_clarification": False,
            "clarification_question": "",
            "requirement_satisfied": True,
            "requirement_evidence": "已尝试",
            "schedule": invalid,
            "change_summary": [],
        }
        second = {
            "understanding": "已根据校验错误修复",
            "needs_clarification": False,
            "clarification_question": "",
            "requirement_satisfied": True,
            "requirement_evidence": "修复后通过",
            "schedule": self.plain,
            "change_summary": [],
        }
        with patch("deepseek_app.revise_schedule", side_effect=[first, second]) as mocked:
            result = run_revision("保持排班合规", self.base["schedule"], self.base["request"])
        self.assertTrue(result["success"])
        self.assertEqual(2, mocked.call_count)


if __name__ == "__main__":
    unittest.main()

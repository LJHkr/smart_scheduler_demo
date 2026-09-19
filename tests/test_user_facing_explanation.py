import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "deepseek_agent"))

from deepseek_app_v5 import fallback_sentences, run_explanation  # noqa: E402
from scheduler import generate_schedule  # noqa: E402


class UserFacingExplanationTests(unittest.TestCase):
    def setUp(self):
        self.base = generate_schedule("生成完整一周排班")
        self.assertTrue(self.base["success"])

    def test_fallback_uses_employee_facing_language(self):
        sentences = fallback_sentences(self.base["schedule"])
        self.assertTrue(sentences)
        forbidden = ["LLM", "Python", "算法", "模型", "校验器", "R-01"]
        for sentence in sentences:
            self.assertFalse(any(word in sentence for word in forbidden), sentence)

    def test_question_returns_only_readable_sentences_without_modifying_schedule(self):
        before = copy.deepcopy(self.base["schedule"])
        explanation = {
            "sentences": ["因为 E01 偏好早班，所以安排在周一早班。"],
            "read_only_confirmation": True,
            "model": "deepseek-flash",
        }
        with patch("deepseek_app_v5.explain_for_user", return_value=explanation):
            result = run_explanation("为什么这样安排？", self.base["schedule"])
        self.assertTrue(result["success"])
        self.assertTrue(result["schedule_unchanged"])
        self.assertEqual(before, self.base["schedule"])
        self.assertEqual(explanation["sentences"], result["explanation"]["sentences"])


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "deepseek_agent"))

from deepseek_app_v6 import unable_result  # noqa: E402
from request_guard import detect_underdetermined_request  # noqa: E402


class BoundaryCaseTests(unittest.TestCase):
    def test_missing_business_volume_returns_unable_to_determine(self):
        detected = detect_underdetermined_request("请根据下周客流量安排人手，高峰多排、低峰少排")
        self.assertIsNotNone(detected)
        result = unable_result("new", detected)
        self.assertFalse(result["success"])
        self.assertTrue(result["unable_to_determine"])
        self.assertTrue(result["needs_clarification"])
        self.assertIn("无法判断", result["clarification_question"])
        self.assertIn("客流", result["clarification_question"])

    def test_performance_ranking_is_not_invented(self):
        detected = detect_underdetermined_request("请优先安排表现最好的员工")
        self.assertIsNotNone(detected)
        self.assertIn("绩效", detected["reason"])

    def test_normal_request_is_not_blocked(self):
        self.assertIsNone(detect_underdetermined_request("生成下周完整排班，尽量满足偏好"))


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scheduler import generate_schedule, load_employees, parse_request, validate_schedule  # noqa: E402


class SchedulerTests(unittest.TestCase):
    def test_full_week_has_valid_schedule(self):
        result = generate_schedule("请生成下周完整排班，尽量满足偏好")
        self.assertTrue(result["success"], result.get("error"))
        self.assertEqual(14, len(result["schedule"]))
        self.assertTrue(result["validation"]["valid"])

    def test_weekend_request_is_parsed(self):
        request = parse_request("只生成周末排班")
        self.assertEqual(["周六", "周日"], request["days"])

    def test_validator_detects_missing_manager(self):
        employees = load_employees()
        request = parse_request("只排周一早班")
        invalid = [{"day": "周一", "shift": "早班", "employees": ["E06", "E07", "E08", "E12"]}]
        validation = validate_schedule(invalid, employees, request)
        self.assertFalse(validation["valid"])
        self.assertFalse(validation["rules"]["R-01"]["passed"])


if __name__ == "__main__":
    unittest.main()

import unittest
from app import bar, humanize_duration, render
from datetime import datetime, timezone, timedelta


class BarTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(bar(0), "░░░░░░░░░░")

    def test_full(self):
        self.assertEqual(bar(100), "██████████")

    def test_half(self):
        self.assertEqual(bar(50), "█████░░░░░")

    def test_rounds_down(self):
        # 19% -> 1.9 segments -> 1 filled
        self.assertEqual(bar(19), "█░░░░░░░░░")

    def test_clamps_over_100(self):
        self.assertEqual(bar(150), "██████████")

    def test_clamps_negative(self):
        self.assertEqual(bar(-5), "░░░░░░░░░░")


class HumanizeDurationTests(unittest.TestCase):
    def test_seconds_show_as_less_than_a_minute(self):
        self.assertEqual(humanize_duration(30), "<1m")

    def test_minutes(self):
        self.assertEqual(humanize_duration(5 * 60), "5m")

    def test_hours_drop_minutes(self):
        self.assertEqual(humanize_duration(3 * 3600 + 45 * 60), "3h")

    def test_days_drop_hours(self):
        self.assertEqual(humanize_duration(2 * 86400 + 5 * 3600), "2d")

    def test_negative_is_zero(self):
        self.assertEqual(humanize_duration(-100), "<1m")


if __name__ == "__main__":
    unittest.main()

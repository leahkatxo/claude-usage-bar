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


FIXED_NOW = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)


def _usage(**overrides):
    base = {
        "five_hour": {"utilization": 2.0, "resets_at": "2026-04-15T15:00:00+00:00"},
        "seven_day": {"utilization": 19.0, "resets_at": "2026-04-20T10:00:00+00:00"},
        "seven_day_sonnet": {"utilization": 2.0, "resets_at": "2026-04-16T10:00:00+00:00"},
        "seven_day_opus": None,
    }
    base.update(overrides)
    return base


class RenderTests(unittest.TestCase):
    def test_title_uses_max_utilization(self):
        out = render(_usage(), now=FIXED_NOW)
        self.assertIn("19%", out["title"])

    def test_title_green_dot_under_60(self):
        out = render(_usage(), now=FIXED_NOW)
        self.assertTrue(out["title"].startswith("🟢"))

    def test_title_orange_dot_60_to_84(self):
        out = render(_usage(seven_day={"utilization": 70, "resets_at": "2026-04-20T10:00:00+00:00"}), now=FIXED_NOW)
        self.assertTrue(out["title"].startswith("🟠"))

    def test_title_red_dot_85_plus(self):
        out = render(_usage(seven_day={"utilization": 90, "resets_at": "2026-04-20T10:00:00+00:00"}), now=FIXED_NOW)
        self.assertTrue(out["title"].startswith("🔴"))

    def test_items_include_three_rows(self):
        out = render(_usage(), now=FIXED_NOW)
        labels = [it["label"] for it in out["items"]]
        self.assertEqual(labels, ["5-hour", "Week", "Sonnet"])

    def test_item_shows_bar_pct_and_reset(self):
        out = render(_usage(), now=FIXED_NOW)
        five_hour = out["items"][0]
        self.assertIn("░░░░░░░░░░", five_hour["text"])
        self.assertIn("2%", five_hour["text"])
        self.assertIn("5h", five_hour["text"])

    def test_null_sublimit_hidden(self):
        out = render(_usage(seven_day_sonnet=None), now=FIXED_NOW)
        labels = [it["label"] for it in out["items"]]
        self.assertNotIn("Sonnet", labels)

    def test_opus_shown_when_present(self):
        out = render(
            _usage(seven_day_opus={"utilization": 40, "resets_at": "2026-04-17T10:00:00+00:00"}),
            now=FIXED_NOW,
        )
        labels = [it["label"] for it in out["items"]]
        self.assertIn("Opus", labels)


if __name__ == "__main__":
    unittest.main()

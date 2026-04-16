"""Claude Usage Bar — menu bar app showing Claude Code quota usage."""

import json
import subprocess
import requests
from datetime import datetime, timezone

BAR_WIDTH = 10
KEYCHAIN_SERVICE = "Claude Code-credentials"
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
HTTP_TIMEOUT = 10


def read_token() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    return payload["claudeAiOauth"]["accessToken"]


def fetch_usage(token: str) -> dict:
    resp = requests.get(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
        },
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def bar(pct: float) -> str:
    pct = max(0.0, min(100.0, float(pct)))
    filled = int(pct / 100 * BAR_WIDTH)
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def humanize_duration(seconds: float) -> str:
    s = max(0, int(seconds))
    if s < 60:
        return "<1m"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


ROWS = [
    ("5-hour", "five_hour"),
    ("Week", "seven_day"),
    ("Sonnet", "seven_day_sonnet"),
    ("Opus", "seven_day_opus"),
]


def _dot(max_pct: float) -> str:
    if max_pct >= 85:
        return "🔴"
    if max_pct >= 60:
        return "🟠"
    return "🟢"


def _format_row(label: str, block: dict, now: datetime) -> dict:
    pct = block["utilization"]
    pct_int = int(round(pct))
    resets_at = block.get("resets_at")
    if resets_at:
        reset_dt = datetime.fromisoformat(resets_at)
        delta_s = (reset_dt - now).total_seconds()
        reset_str = f"resets in {humanize_duration(delta_s)}"
    else:
        reset_str = ""
    text = f"{label:<8}{bar(pct)} {pct_int:>3}%   {reset_str}".rstrip()
    return {"label": label, "text": text}


def render(usage: dict, now=None) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)

    items = []
    percents = []
    for label, key in ROWS:
        block = usage.get(key)
        if not block:
            continue
        items.append(_format_row(label, block, now))
        percents.append(block["utilization"])

    max_pct = max(percents) if percents else 0
    title = f"{_dot(max_pct)} {int(round(max_pct))}%"
    return {"title": title, "items": items}


def run_once() -> None:
    try:
        usage = fetch_usage(read_token())
    except subprocess.CalledProcessError:
        print("⚠  Could not read token from keychain. Sign in to Claude Code first.")
        return
    except requests.RequestException as e:
        print(f"⚠  API error: {e}")
        return

    view = render(usage)
    print(view["title"])
    for item in view["items"]:
        print("  " + item["text"])


import rumps

REFRESH_SECONDS = 5 * 60


class UsageBarApp(rumps.App):
    def __init__(self):
        super().__init__("⋯", quit_button=None)
        self.last_good_title = "⋯"
        self.timer = rumps.Timer(self.tick, REFRESH_SECONDS)
        self.timer.start()
        self.tick(None)

    def tick(self, _sender):
        try:
            usage = fetch_usage(read_token())
        except subprocess.CalledProcessError:
            self._show_error("Sign in to Claude Code first.")
            return
        except (requests.RequestException, ValueError) as e:
            self._show_error(f"API error: {e}")
            return

        view = render(usage)
        self.title = view["title"]
        self.last_good_title = view["title"]

        menu_items = [rumps.MenuItem(item["text"]) for item in view["items"]]
        menu_items.append(rumps.separator)
        menu_items.append(rumps.MenuItem(f"Last updated: {datetime.now().strftime('%H:%M')}"))
        menu_items.append(rumps.MenuItem("Refresh now", callback=self.manual_refresh))
        menu_items.append(rumps.MenuItem("Quit", callback=rumps.quit_application))
        self.menu.clear()
        self.menu = menu_items

    def _show_error(self, msg: str):
        self.title = "⚠ " + self.last_good_title.lstrip("🟢🟠🔴⚠ ").strip()
        self.menu.clear()
        self.menu = [
            rumps.MenuItem(msg),
            rumps.separator,
            rumps.MenuItem("Refresh now", callback=self.manual_refresh),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

    def manual_refresh(self, _sender):
        self.tick(None)


if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        run_once()
        sys.exit(0)
    UsageBarApp().run()

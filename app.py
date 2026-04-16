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

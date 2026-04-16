"""Claude Usage Bar — menu bar app showing Claude Code quota usage."""

BAR_WIDTH = 10


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


def render(usage: dict, now=None):
    raise NotImplementedError

"""Claude Usage Bar — menu bar app showing Claude Code quota usage."""

import json
import os
import subprocess
import requests
from datetime import datetime, timezone

BAR_WIDTH = 10
KEYCHAIN_SERVICE = "Claude Code-credentials"
ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

# Pastel palette
COLORS = {
    "teal":  (0.49, 0.84, 0.77),   # #7CD5C4 — low usage
    "peach": (1.00, 0.73, 0.59),    # #FFBA97 — medium usage
    "rose":  (1.00, 0.56, 0.67),    # #FF8FAB — high usage
    "lilac": (0.77, 0.72, 0.92),    # #C4B7EA — warning/error
}


def _generate_icons():
    """Create tiny colored-circle PNGs for the menu bar using AppKit."""
    os.makedirs(ICON_DIR, exist_ok=True)
    try:
        import AppKit
    except ImportError:
        return  # PyObjC not available; emoji fallback
    size = 32
    for name, (r, g, b) in COLORS.items():
        path = os.path.join(ICON_DIR, f"{name}.png")
        if os.path.exists(path):
            continue
        img = AppKit.NSImage.alloc().initWithSize_((size, size))
        img.lockFocus()
        color = AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0)
        color.setFill()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(((4, 4), (size - 8, size - 8))).fill()
        img.unlockFocus()
        tiff = img.TIFFRepresentation()
        bitmap = AppKit.NSBitmapImageRep.alloc().initWithData_(tiff)
        png_data = bitmap.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {})
        png_data.writeToFile_atomically_(path, True)


def _icon_path(max_pct: float) -> str:
    if max_pct >= 85:
        name = "rose"
    elif max_pct >= 60:
        name = "peach"
    else:
        name = "teal"
    return os.path.join(ICON_DIR, f"{name}.png")
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
    return {"label": label, "text": text, "pct": pct, "reset_str": reset_str}


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
    return {"title": title, "title_text": f" {int(round(max_pct))}%", "icon": _icon_path(max_pct), "items": items}


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
try:
    import AppKit
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False

REFRESH_SECONDS = 5 * 60

# Font for dropdown items — monospace so bars align
MENU_FONT = AppKit.NSFont.monospacedSystemFontOfSize_weight_(13, AppKit.NSFontWeightMedium) if HAS_APPKIT else None

# Attributed-string colors (NSColor) for dropdown
AS_COLORS = {}
if HAS_APPKIT:
    AS_COLORS = {
        "label": AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.85, 0.85, 0.88, 1.0),
        "pct":   AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.95, 0.95, 0.97, 1.0),
        "empty": AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.35, 0.35, 0.38, 1.0),
        "teal":  AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.49, 0.84, 0.77, 1.0),
        "peach": AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(1.00, 0.73, 0.59, 1.0),
        "rose":  AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(1.00, 0.56, 0.67, 1.0),
        "meta":  AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.55, 0.55, 0.58, 1.0),
    }


def _bar_color_for_pct(pct: float):
    if pct >= 85:
        return AS_COLORS["rose"]
    if pct >= 60:
        return AS_COLORS["peach"]
    return AS_COLORS["teal"]


def _styled_menu_item(item: dict) -> rumps.MenuItem:
    """Build an NSMenuItem with colored attributed title."""
    mi = rumps.MenuItem(item["text"])  # plain fallback
    if not HAS_APPKIT:
        return mi

    label = item["label"]
    pct = item["pct"]
    filled = int(max(0.0, min(100.0, float(pct))) / 100 * BAR_WIDTH)
    empty = BAR_WIDTH - filled
    reset_str = item.get("reset_str", "")

    attrs_label = {AppKit.NSFontAttributeName: MENU_FONT, AppKit.NSForegroundColorAttributeName: AS_COLORS["label"]}
    attrs_filled = {AppKit.NSFontAttributeName: MENU_FONT, AppKit.NSForegroundColorAttributeName: _bar_color_for_pct(pct)}
    attrs_empty = {AppKit.NSFontAttributeName: MENU_FONT, AppKit.NSForegroundColorAttributeName: AS_COLORS["empty"]}
    attrs_pct = {AppKit.NSFontAttributeName: MENU_FONT, AppKit.NSForegroundColorAttributeName: AS_COLORS["pct"]}
    attrs_meta = {AppKit.NSFontAttributeName: MENU_FONT, AppKit.NSForegroundColorAttributeName: AS_COLORS["meta"]}

    s = AppKit.NSMutableAttributedString.alloc().init()
    s.appendAttributedString_(AppKit.NSAttributedString.alloc().initWithString_attributes_(f"{label:<8}", attrs_label))
    s.appendAttributedString_(AppKit.NSAttributedString.alloc().initWithString_attributes_("█" * filled, attrs_filled))
    s.appendAttributedString_(AppKit.NSAttributedString.alloc().initWithString_attributes_("░" * empty, attrs_empty))
    s.appendAttributedString_(AppKit.NSAttributedString.alloc().initWithString_attributes_(f" {int(round(pct)):>3}%", attrs_pct))
    if reset_str:
        s.appendAttributedString_(AppKit.NSAttributedString.alloc().initWithString_attributes_(f"   {reset_str}", attrs_meta))

    mi._menuitem.setAttributedTitle_(s)
    return mi


class UsageBarApp(rumps.App):
    def __init__(self):
        super().__init__("⋯", quit_button=None)
        self._template = False  # keep icon colors, don't template
        self.last_good_title = "⋯"
        _generate_icons()
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
        self.title = view["title_text"]
        self.last_good_title = view["title_text"]
        icon_file = view["icon"]
        if os.path.exists(icon_file):
            self.icon = icon_file
        else:
            self.title = view["title"]  # emoji fallback

        menu_items = [_styled_menu_item(item) for item in view["items"]]
        menu_items.append(rumps.separator)
        updated = rumps.MenuItem(f"Last updated: {datetime.now().strftime('%H:%M')}")
        if HAS_APPKIT:
            attrs_meta = {AppKit.NSFontAttributeName: MENU_FONT, AppKit.NSForegroundColorAttributeName: AS_COLORS["meta"]}
            updated._menuitem.setAttributedTitle_(
                AppKit.NSAttributedString.alloc().initWithString_attributes_(
                    f"Last updated: {datetime.now().strftime('%H:%M')}", attrs_meta))
        menu_items.append(updated)
        menu_items.append(rumps.MenuItem("Refresh now", callback=self.manual_refresh))
        menu_items.append(rumps.MenuItem("Quit", callback=rumps.quit_application))
        self.menu.clear()
        self.menu = menu_items

    def _show_error(self, msg: str):
        lilac = os.path.join(ICON_DIR, "lilac.png")
        if os.path.exists(lilac):
            self.icon = lilac
        self.title = self.last_good_title
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

# Claude Usage Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A macOS menu bar app showing Claude Code usage quota bars, pulling data from the same `/api/oauth/usage` endpoint Claude Code's `/usage` view uses.

**Architecture:** Single-file Python app using `rumps` for the menu bar. OAuth token read from macOS Keychain via the `security` command. Polls usage endpoint every 5 minutes. Pure rendering function is unit-tested; I/O functions get a smoke test via `--once` mode. Auto-starts at login via a user launchd agent.

**Tech Stack:** Python 3 (system), `rumps`, `requests`, macOS `security` CLI, macOS `launchctl`.

---

## File Structure

```
~/claude-usage-bar/
├── app.py                                   # Main application (~150 lines)
├── test_app.py                              # Unit tests for render()
├── requirements.txt                         # rumps, requests
├── install.sh                               # pip install + launchctl load
├── uninstall.sh                             # launchctl unload + remove plist
├── com.leah.claude-usage-bar.plist.template # launchd user agent template
├── README.md                                # install / uninstall / troubleshoot
├── .gitignore                               # __pycache__, venv, etc.
└── docs/superpowers/
    ├── specs/2026-04-15-claude-usage-bar-design.md
    └── plans/2026-04-15-claude-usage-bar.md
```

**Responsibilities:**
- `app.py` — CLI entrypoint, rumps app class, token/API I/O, pure render function
- `test_app.py` — unit tests for `render()` against fixture API responses
- `install.sh` / `uninstall.sh` — one-shot setup / teardown
- Plist template — has a `{{PYTHON}}` placeholder that `install.sh` substitutes

---

## Task 1: Scaffold project

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`

- [ ] **Step 1: Create `requirements.txt`**

```
rumps>=0.4.0
requests>=2.31.0
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.DS_Store
com.leah.claude-usage-bar.plist
```

(The generated plist is gitignored — only the template is tracked.)

- [ ] **Step 3: Verify dependencies install**

Run:
```bash
cd ~/claude-usage-bar
python3 -m pip install --user -r requirements.txt
python3 -c "import rumps, requests; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "Scaffold project with dependencies"
```

---

## Task 2: Pure renderer — bar + duration helpers

The `render()` function is the only non-trivial pure logic. Build it TDD.

**Files:**
- Create: `app.py` (skeleton)
- Create: `test_app.py`

- [ ] **Step 1: Write failing test for `bar()`**

Create `test_app.py`:
```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test — expect failure**

Run: `python3 -m unittest test_app.py -v`
Expected: `ImportError: cannot import name 'bar' from 'app'`.

- [ ] **Step 3: Create `app.py` skeleton with `bar()`**

Create `app.py`:
```python
"""Claude Usage Bar — menu bar app showing Claude Code quota usage."""

BAR_WIDTH = 10


def bar(pct: float) -> str:
    pct = max(0.0, min(100.0, float(pct)))
    filled = int(pct / 100 * BAR_WIDTH)
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def humanize_duration(seconds: float) -> str:
    raise NotImplementedError


def render(usage: dict, now=None):
    raise NotImplementedError
```

- [ ] **Step 4: Run tests — `bar` passes**

Run: `python3 -m unittest test_app.BarTests -v`
Expected: all 6 pass.

- [ ] **Step 5: Write failing tests for `humanize_duration()`**

Append to `test_app.py`:
```python
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
```

- [ ] **Step 6: Run — expect failures**

Run: `python3 -m unittest test_app.HumanizeDurationTests -v`
Expected: 5 failures with `NotImplementedError`.

- [ ] **Step 7: Implement `humanize_duration()`**

Replace `humanize_duration` in `app.py`:
```python
def humanize_duration(seconds: float) -> str:
    s = max(0, int(seconds))
    if s < 60:
        return "<1m"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"
```

- [ ] **Step 8: Run — expect passes**

Run: `python3 -m unittest test_app -v`
Expected: all 11 tests pass.

- [ ] **Step 9: Commit**

```bash
git add app.py test_app.py
git commit -m "Add bar() and humanize_duration() with tests"
```

---

## Task 3: Pure renderer — `render()` function

**Files:**
- Modify: `app.py`
- Modify: `test_app.py`

- [ ] **Step 1: Write failing tests for `render()`**

Append to `test_app.py`:
```python
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
        # 5h=2, week=19, sonnet=2 -> max=19
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
        # 2% -> 0 filled segments
        self.assertIn("░░░░░░░░░░", five_hour["text"])
        self.assertIn("2%", five_hour["text"])
        # resets in 5 hours
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
```

- [ ] **Step 2: Run — expect failures**

Run: `python3 -m unittest test_app.RenderTests -v`
Expected: 8 failures with `NotImplementedError`.

- [ ] **Step 3: Implement `render()`**

Replace `render` in `app.py` and add supporting imports and constants at the top of the file:
```python
from datetime import datetime, timezone

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
```

- [ ] **Step 4: Run — expect passes**

Run: `python3 -m unittest test_app -v`
Expected: all 19 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app.py test_app.py
git commit -m "Add render() with full test coverage"
```

---

## Task 4: Keychain token reader

`read_token()` shells out to `security` and parses the JSON blob. Not unit-testable without heavy mocking; we verify with a smoke test.

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add `read_token()`**

Add to `app.py` (after the imports):
```python
import json
import subprocess

KEYCHAIN_SERVICE = "Claude Code-credentials"


def read_token() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    return payload["claudeAiOauth"]["accessToken"]
```

Note: we don't pass `-a $USER` — `security` defaults to searching across accounts, and there's only one entry for this service.

- [ ] **Step 2: Smoke-test it**

Run:
```bash
python3 -c "from app import read_token; t = read_token(); print('len=', len(t), 'starts_with=', t[:15])"
```
Expected: prints e.g. `len= 108 starts_with= sk-ant-oat01-XX`.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "Add read_token() from macOS keychain"
```

---

## Task 5: Usage fetcher

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add `fetch_usage()`**

Add to `app.py` (after imports add `import requests`):
```python
import requests

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
HTTP_TIMEOUT = 10


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
```

- [ ] **Step 2: Smoke-test it**

Run:
```bash
python3 -c "from app import read_token, fetch_usage; import json; print(json.dumps(fetch_usage(read_token()), indent=2))"
```
Expected: prints a JSON object with `five_hour`, `seven_day`, etc.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "Add fetch_usage() against /api/oauth/usage"
```

---

## Task 6: `--once` CLI mode (end-to-end smoke test)

Before wiring up `rumps`, expose the full flow as a one-shot CLI so we can verify and diagnose without the menu bar.

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add `run_once()` and `__main__` branch**

Append to `app.py`:
```python
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


if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        run_once()
        sys.exit(0)
    # The rumps app entrypoint is added in Task 7.
    print("Pass --once for a single snapshot. Menu bar mode not wired up yet.")
```

- [ ] **Step 2: Run it**

Run: `python3 app.py --once`
Expected: prints something like:
```
🟢 19%
  5-hour  ░░░░░░░░░░   2%   resets in 5h
  Week    █░░░░░░░░░  19%   resets in 5d
  Sonnet  ░░░░░░░░░░   2%   resets in 23h
```

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "Add --once CLI mode for smoke testing"
```

---

## Task 7: Menu bar app (rumps integration)

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add `UsageBarApp` class**

Append to `app.py` (before the `if __name__ == "__main__":` block):
```python
import rumps

REFRESH_SECONDS = 5 * 60


class UsageBarApp(rumps.App):
    def __init__(self):
        super().__init__("⋯", quit_button=None)
        self.last_good_title = "⋯"
        self.last_error = None
        self.refresh_item = rumps.MenuItem("Refresh now", callback=self.manual_refresh)
        self.updated_item = rumps.MenuItem("Last updated: never")
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
        self.last_error = None

        menu_items = [rumps.MenuItem(item["text"]) for item in view["items"]]
        menu_items.append(rumps.separator)
        menu_items.append(rumps.MenuItem(f"Last updated: {datetime.now().strftime('%H:%M')}"))
        menu_items.append(self.refresh_item)
        menu_items.append(rumps.MenuItem("Quit", callback=rumps.quit_application))
        self.menu.clear()
        self.menu = menu_items

    def _show_error(self, msg: str):
        self.title = "⚠ " + self.last_good_title.lstrip("🟢🟠🔴⚠ ").strip()
        self.last_error = msg
        self.menu.clear()
        self.menu = [
            rumps.MenuItem(msg),
            rumps.separator,
            self.refresh_item,
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

    def manual_refresh(self, _sender):
        self.tick(None)
```

- [ ] **Step 2: Update `__main__` to launch the app**

Replace the existing `if __name__ == "__main__":` block:
```python
if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        run_once()
        sys.exit(0)
    UsageBarApp().run()
```

- [ ] **Step 3: Launch and verify**

Run: `python3 app.py`
Expected: a green/orange/red dot with a % appears in the top-right menu bar. Clicking it shows 3 bars, "Last updated: HH:MM", "Refresh now", "Quit". Click "Refresh now" and the updated time changes. Click "Quit" to exit.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "Wire up rumps menu bar app with 5-minute refresh"
```

---

## Task 8: Launchd auto-launch

**Files:**
- Create: `com.leah.claude-usage-bar.plist.template`
- Create: `install.sh`
- Create: `uninstall.sh`

- [ ] **Step 1: Create plist template**

Create `com.leah.claude-usage-bar.plist.template`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.leah.claude-usage-bar</string>
  <key>ProgramArguments</key>
  <array>
    <string>{{PYTHON}}</string>
    <string>{{APP_DIR}}/app.py</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{{APP_DIR}}/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>{{APP_DIR}}/launchd.err.log</string>
</dict>
</plist>
```

- [ ] **Step 2: Create `install.sh`**

Create `install.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.leah.claude-usage-bar.plist"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"
PYTHON="$(which python3)"

echo "→ Installing Python dependencies"
"$PYTHON" -m pip install --user -r "$APP_DIR/requirements.txt"

echo "→ Rendering launchd plist → $TARGET"
mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s|{{PYTHON}}|$PYTHON|g" \
    -e "s|{{APP_DIR}}|$APP_DIR|g" \
    "$APP_DIR/$PLIST_NAME.template" > "$TARGET"

echo "→ Unloading any existing agent (ignoring errors)"
launchctl unload "$TARGET" 2>/dev/null || true

echo "→ Loading agent"
launchctl load "$TARGET"

echo "✓ Installed. The menu bar icon should appear shortly."
echo "  Logs: $APP_DIR/launchd.{out,err}.log"
echo "  Uninstall with: $APP_DIR/uninstall.sh"
```

- [ ] **Step 3: Create `uninstall.sh`**

Create `uninstall.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

PLIST_NAME="com.leah.claude-usage-bar.plist"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

if [[ -f "$TARGET" ]]; then
  echo "→ Unloading agent"
  launchctl unload "$TARGET" 2>/dev/null || true
  echo "→ Removing $TARGET"
  rm -f "$TARGET"
  echo "✓ Uninstalled."
else
  echo "No agent installed at $TARGET — nothing to do."
fi
```

- [ ] **Step 4: Make scripts executable**

Run: `chmod +x install.sh uninstall.sh`

- [ ] **Step 5: Test install**

Run:
```bash
# Make sure the foreground app from Task 7 is quit first.
./install.sh
sleep 3
launchctl list | grep com.leah.claude-usage-bar
```
Expected: last command prints a line like `PID  0  com.leah.claude-usage-bar`. A new menu bar icon should be visible.

- [ ] **Step 6: Test uninstall and re-install**

Run:
```bash
./uninstall.sh
launchctl list | grep com.leah.claude-usage-bar || echo "gone"
./install.sh
```
Expected: first grep prints `gone`; re-install succeeds and icon reappears.

- [ ] **Step 7: Commit**

```bash
git add com.leah.claude-usage-bar.plist.template install.sh uninstall.sh
git commit -m "Add launchd plist template and install/uninstall scripts"
```

---

## Task 9: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

Create `README.md`:
```markdown
# Claude Usage Bar

A tiny macOS menu bar app that shows your Claude Code quota bars so you don't
have to open `/usage` or dig through settings.

![example: `🟢 19%` in the menu bar, click for bars]

## What it shows

- **5-hour** rolling session limit
- **Week** limit (7-day rolling)
- **Sonnet** / **Opus** weekly sub-limits (when present)

Each row has a 10-segment bar, the utilization %, and a reset countdown.
Dot color: green < 60%, orange 60–84%, red ≥ 85%.

## Install

```bash
cd ~/claude-usage-bar
./install.sh
```

That will:
1. `pip install --user` the two dependencies (`rumps`, `requests`).
2. Drop a launchd user agent at
   `~/Library/LaunchAgents/com.leah.claude-usage-bar.plist`.
3. Start the app now and at every login.

## Uninstall

```bash
./uninstall.sh
```

## How it works

The app reads your Claude Code OAuth token from the macOS Keychain
(service `Claude Code-credentials`) and calls
`https://api.anthropic.com/api/oauth/usage` — the same endpoint that powers
Claude Code's `/usage` view. It polls every 5 minutes.

## Troubleshooting

- **Icon shows `⚠`**: click it to see the error. Most common causes: not
  signed in to Claude Code, or no network.
- **Icon didn't appear after install**: check `launchd.err.log` in this
  directory. Often a Python path issue — rerun `./install.sh`.
- **Manually run once**: `python3 app.py --once` prints a single snapshot
  to the terminal.

## Development

Tests: `python3 -m unittest test_app -v`
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Add README"
```

---

## Final verification

- [ ] **Step 1: All tests pass**

Run: `python3 -m unittest test_app -v`
Expected: 19 tests, all pass.

- [ ] **Step 2: Installed agent is running**

Run: `launchctl list | grep com.leah.claude-usage-bar`
Expected: a line with a PID (not `-`) in the first column.

- [ ] **Step 3: Menu bar icon is live**

Visually: see the colored-dot + % indicator in the macOS menu bar. Click it.
Expected: three bar rows, last-updated time, Refresh now, Quit.

- [ ] **Step 4: Restart to confirm auto-launch**

Log out and log back in (or reboot). After logging back in:
Expected: icon reappears automatically within ~5 seconds.

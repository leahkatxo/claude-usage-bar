# Claude Usage Bar — Design

A macOS menu bar app that displays Claude Code usage quota bars at a glance,
without needing to open `/usage` inside Claude Code.

## Goals

- Always-visible indicator of current quota utilization in the macOS menu bar.
- One click to see the full breakdown (5-hour, weekly, weekly-per-model).
- No separate login — reuse the OAuth token Claude Code already stores.
- Small enough to understand and modify as a learning project.

## Non-goals

- Historical charts or trend tracking.
- Notifications / alerts.
- Windows or Linux support.
- Multiple accounts.
- Distribution as a signed `.app` bundle.

## Data source

The Claude Code CLI powers its `/usage` view by calling
`GET https://api.anthropic.com/api/oauth/usage` with the user's OAuth access
token.

- **Token storage:** macOS Keychain, service `Claude Code-credentials`,
  account = `$USER`. Value is a JSON blob; the access token is at
  `claudeAiOauth.accessToken`.
- **Required headers:** `Authorization: Bearer <token>`,
  `anthropic-beta: oauth-2025-04-20`.
- **Response shape (fields we use):**
  ```json
  {
    "five_hour":        { "utilization": <0-100>, "resets_at": <ISO-8601> },
    "seven_day":        { "utilization": <0-100>, "resets_at": <ISO-8601> },
    "seven_day_sonnet": { "utilization": <0-100>, "resets_at": <ISO-8601> | null },
    "seven_day_opus":   { "utilization": <0-100>, "resets_at": <ISO-8601> | null } | null
  }
  ```
  Sub-limits that come back as `null` are simply not shown.

## Architecture

Single-file Python app, `~/claude-usage-bar/app.py`, using the
[`rumps`](https://github.com/jaredks/rumps) library for the menu bar integration
and `requests` for the HTTP call.

```
 launchd (at login)
      │
      ▼
 app.py  ──┐
           ├─ rumps.App (menu bar icon + dropdown)
           ├─ Timer (every 5 min) ──► fetch_usage()
           │                              │
           │        keychain ─────────────┘
           │           │
           │           ▼
           │   https://api.anthropic.com/api/oauth/usage
           │
           └─ render_menu(usage) ──► update title + dropdown items
```

Three small functions, each independently testable:

| Function | Input | Output | Notes |
|---|---|---|---|
| `read_token()` | — | `str` | Shells out to `security find-generic-password`, parses JSON. |
| `fetch_usage(token)` | `str` | `dict` | One HTTP GET, raises on non-200. |
| `render(usage)` | `dict` | title string + list of menu items | Pure function; no I/O. |

## UI

**Menu bar title** shows the highest current utilization:
- `● 19%` — green dot when max utilization < 60%
- `● 65%` — orange dot at 60–84%
- `● 90%` — red dot at ≥85%

**Dropdown** (shown on click):
```
5-hour   ██░░░░░░░░   2%   resets in 14h
Week     ██░░░░░░░░  19%   resets in 5d
Sonnet   █░░░░░░░░░   2%   resets in 23h
──────────────
Last updated: 15:42
Refresh now
Quit
```

- Bars: 10 segments of `█` / `░`.
- Reset countdown uses the largest whole unit (`5d`, `14h`, `23m`).
- Sub-limits (Sonnet, Opus, extra credits) appear only when the API returns a
  non-null block for them.
- `Refresh now` forces an immediate poll.
- "Launch at login" is **not** a toggle in the menu — it's installed once by
  the setup script (see below).

## Refresh

- Every **5 minutes**, via `rumps.Timer`.
- Also on app launch.
- Also when the user clicks `Refresh now`.

## Error handling

Boundary errors only — nothing fancy.

| Failure | Behavior |
|---|---|
| Keychain read fails | Title becomes `⚠`; dropdown shows "Sign in to Claude Code first." |
| HTTP non-200 / network error | Title becomes `⚠ NN%` (last good value if any); dropdown shows error message + time of last success. |
| JSON parse error | Same as HTTP error. |

No retries, no exponential backoff — the next 5-minute tick is the retry.

## Auto-launch at login

A launchd user agent installed at `~/Library/LaunchAgents/com.leah.claude-usage-bar.plist`
that runs `/usr/bin/env python3 ~/claude-usage-bar/app.py` with
`RunAtLoad=true` and `KeepAlive=true` (restart if it crashes).

Install / uninstall is handled by a tiny `install.sh` / `uninstall.sh` pair
next to `app.py`.

## File layout

```
~/claude-usage-bar/
├── app.py               # the menu bar app (one file, ~150 lines)
├── install.sh           # pip install + launchctl load
├── uninstall.sh         # launchctl unload + remove plist
├── com.leah.claude-usage-bar.plist.template
├── README.md            # how to install / uninstall / troubleshoot
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-15-claude-usage-bar-design.md
```

## Dependencies

- Python 3 (already on macOS).
- `rumps` and `requests` installed via `pip install --user`.
- No other external tools beyond built-in `security` and `launchctl`.

## Testing

- `render(usage)` is a pure function and gets unit tests against a small fixture
  of API responses (full response, missing sub-limits, all-null sub-limits).
- `read_token()` and `fetch_usage()` are exercised manually at install time by
  running `python3 app.py --once`, which prints one rendered snapshot to stdout
  and exits.
- No test harness beyond `python3 -m unittest`.

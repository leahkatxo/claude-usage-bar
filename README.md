# Claude Usage Bar

A tiny macOS menu bar app that shows your Claude Code quota bars so you don't
have to open `/usage` or dig through settings.

## What it shows

- **5-hour** rolling session limit
- **Week** limit (7-day rolling)
- **Sonnet** / **Opus** weekly sub-limits (when present)

Each row has a 10-segment bar, the utilization %, and a reset countdown.
Dot color: green < 60%, orange 60-84%, red >= 85%.

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
`https://api.anthropic.com/api/oauth/usage` -- the same endpoint that powers
Claude Code's `/usage` view. It polls every 5 minutes.

## Troubleshooting

- **Icon shows a warning**: click it to see the error. Most common causes: not
  signed in to Claude Code, or no network.
- **Icon didn't appear after install**: check `launchd.err.log` in this
  directory. Often a Python path issue -- rerun `./install.sh`.
- **Manually run once**: `python3 app.py --once` prints a single snapshot
  to the terminal.

## Development

Tests: `python3 -m unittest test_app -v`

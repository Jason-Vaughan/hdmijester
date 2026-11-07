# Changelog

All notable changes to HDMIJester are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Link badge stayed `CLEAN` after a disconnect that logged no DCP hotplug event. Some USB-C→HDMI dongles drop the display without any hotplug/sink-count message, so the log-derived `connected` flag never flipped. The badge now reads `DISCONNECTED` whenever the display-presence poll reports no external display, independent of whether a log event fired.
- Dashboard header showed the built-in panel instead of the external HDMI display. `display_mode()` reported the first display `system_profiler` lists, which on a laptop is always the built-in `Color LCD`. It now skips the internal panel, lists **every** attached external display, and re-polls every few seconds so plugging a monitor in is reflected live without restarting `hdmijester-watch`.
- Detect unplug/replug from the DCP `handleSinkCountChanged` message. WindowServer's "not active" line isn't logged on every cable swap, so three unplugs at 19:49–19:50 on 2026-10-14 went uncounted.

### Changed

- Project folder renamed to `~/Documents/Projects/hdmi-watch`. All output (CSV runs, snapshots) now goes to the git-ignored `captures/` directory in the repo instead of the Desktop.
- Renamed the project and its CLI from HDMI-Watch (`hdmi-watch` / `hdmi-snapshot`) to **HDMIJester** (`hdmijester-watch` / `hdmijester-snapshot`) ahead of its public release.

### Added

- `--version` flag on `hdmijester-watch` and `hdmijester-snapshot`, printing the project version from `.tangleclaw/project-version.txt`.
- Logo, hosted in [project-assets](https://github.com/Jason-Vaughan/project-assets) and embedded in the README.
- AGPL-3.0 `LICENSE` for public release.

## [0.1.0] - 2026-10-14

### Added

- `bin/hdmi-watch`: live curses dashboard of HDMI link health from the DCP unified-log messages. It shows CED character-error counts per TMDS lane, the link-status-change rate, a 60 s per-second graph, hotplug, HPD and link-stability events, labelled test segments (auto-segment on reconnect), and a per-run CSV.
- `bin/hdmi-snapshot`: evidence file for warranty or return cases, with hardware and display config (serials removed), a per-minute summary and raw events, since boot or for a chosen range.
- Polling via `/usr/bin/log show`, because `log stream` doesn't deliver DCP messages; events are bucketed by event time.
- Parser tests on real log lines (`tests/test_parse.py`).
- Docs: README, `docs/HOW-IT-WORKS.md`, `docs/TESTING-GUIDE.md`.

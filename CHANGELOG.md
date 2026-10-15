# Changelog

All notable changes to HDMI-Watch are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Detect unplug/replug from the DCP `handleSinkCountChanged` message. WindowServer's "not active" line isn't logged on every cable swap, so three unplugs at 19:49–19:50 on 2026-10-14 went uncounted.

### Changed

- Project folder renamed to `~/Documents/Projects/hdmi-watch`. All output (CSV runs, snapshots) now goes to the git-ignored `captures/` directory in the repo instead of the Desktop.

## [0.1.0] - 2026-10-14

### Added

- `bin/hdmi-watch`: live curses dashboard of HDMI link health from the DCP unified-log messages. It shows CED character-error counts per TMDS lane, the link-status-change rate, a 60 s per-second graph, hotplug, HPD and link-stability events, labelled test segments (auto-segment on reconnect), and a per-run CSV.
- `bin/hdmi-snapshot`: evidence file for warranty or return cases, with hardware and display config (serials removed), a per-minute summary and raw events, since boot or for a chosen range.
- Polling via `/usr/bin/log show`, because `log stream` doesn't deliver DCP messages; events are bucketed by event time.
- Parser tests on real log lines (`tests/test_parse.py`).
- Docs: README, `docs/HOW-IT-WORKS.md`, `docs/TESTING-GUIDE.md`.

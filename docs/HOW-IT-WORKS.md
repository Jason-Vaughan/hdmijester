# How HDMIJester works

## Where the data comes from

On Apple Silicon, displays are driven by the **DCP** (Display Coprocessor), a separate firmware core. Its log messages appear in the unified log tagged `(DCP)` from the `kernel` process, and `senderImagePath` contains `DCP`.

For HDMI ports (the Mac Studio HDMI port is driven through an `AppleDCPMCDP29XX` DP→HDMI converter), the DCP enables **HDMI link status monitoring** with SCDC (Status and Control Data Channel). The monitor counts **character errors** on each of the three TMDS data lanes and raises an interrupt when they change. The DCP logs them:

| Message | Meaning | Parsed as |
|---|---|---|
| `AppleDCPDPTXController::handleIrqHpdEvent dispatching IRQ_HPD` | The sink raised an interrupt | (not counted, it always pairs with the next line) |
| `handleIRQHDMILinkStatusChanged HDMI link status changed` | The sink reports a link status change | `linkchg` |
| `hdmiCharacterErrorDetectionUpdate CED error count update: [L0][L1][L2]` | Error counts per lane | `ced` (the three numbers) |
| `checkLinkGated ... link[0]Stable=YES/NO` | DCP's own link stability check | `unstable` when `NO` |
| `ConfigChange: HPD a->b` | Hot Plug Detect pin change | `hpd` when a ≠ b |
| `handleSinkCountChanged oldCount=a newCount=b` | Monitor (sink) attached or removed: **the most reliable plug/unplug signal** | `hotplug` (b > 0 = connected) |

WindowServer logs display attach and detach:

| Message | Parsed as |
|---|---|
| `Display 1 hotplug-state 1 updating digital modes` | `hotplug 1` (connected) |
| `Display 1 get_hotplug_state - not active` | `hotplug 0` (disconnected) |

Only display slot 1 (the main external display) is tracked. Slots 2–5 report "not active" at boot on a single-display setup and are ignored.

**On a healthy link there are essentially no CED reports.** A report every few seconds means the sink keeps seeing errors.

## Why polling and not `log stream`

`log stream --predicate 'senderImagePath CONTAINS "DCP"'` **never delivers** these messages. Testing on macOS 26.7.1 returned zero CED lines in 10 s, while `log show` for the same window found them. DCP messages appear to be forwarded from the coprocessor into the log store by a path the live stream doesn't tap.

So `poll_lines()` runs `/usr/bin/log show --start <last-seen − 4 s>` about once a second (~0.7 s per call), keeps an LRU set of the last 5,000 lines to drop the overlap, and yields `(event_time, line)`. The dashboard buckets errors by **event time** and draws the graph up to `now − 2 s`, so batching in delivery doesn't distort it.

Use `/usr/bin/log` explicitly: zsh has a built-in `log` command that shadows it and silently returns nothing.

## Segments

A segment is one test condition. The dashboard keeps:

- `ced_reports`: number of CED reports
- `lane_sum` and `lane_max`: per-lane totals and maxima
- `disconnects` and `unstable`: counts

`reports/min` is the most robust comparison number. `err/min` (summed lane counts per minute) is more sensitive but depends on how the sink counts.

A reconnect (hotplug 0 → 1) starts a new segment automatically, so swapping a cable doesn't need a keypress. Press `n` to label it.

## Files

| Path | Purpose |
|---|---|
| `bin/hdmijester-watch` | Curses dashboard (Python 3, stdlib only) |
| `bin/hdmijester-snapshot` | Evidence file: hardware, per-minute summary, raw events (bash + awk) |
| `tests/test_parse.py` | Parser tests on real log lines |
| `captures/hdmijester-snapshot-*.txt` (git-ignored) | Evidence snapshots |
| `captures/hdmijester-watch-*.csv` (git-ignored) | Per-run event log: `time, segment, event, lane0, lane1, lane2, detail` |

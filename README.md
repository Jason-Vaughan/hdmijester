<img src="https://raw.githubusercontent.com/Jason-Vaughan/project-assets/main/hdmijester-logo.png" alt="HDMIJester logo" width="220">

# HDMIJester

*Because HDMI is no laughing matter. Every handshake tells a story.*

A live terminal dashboard for **HDMI link errors on Apple Silicon Macs**. Use it to work out whether a flaky external display is caused by the cable, the monitor, or the Mac, and to collect evidence for a warranty or return claim.

macOS doesn't show HDMI signal quality anywhere in its interface. The display coprocessor (DCP) does log it, though. When the monitor reports bit errors on the HDMI wire, the DCP writes *HDMI Character Error Detection* (CED) counts for each data lane to the unified log, together with "HDMI link status changed" interrupts. HDMIJester reads those messages every second and presents them as numbers you can compare across cables and ports.

![status: works on macOS 26 / Mac Studio M1 Max](https://img.shields.io/badge/tested-macOS%2026.7%20%C2%B7%20Mac13%2C1-blue)

## Why it exists

A new Mac Studio (M1 Max, `Mac13,1`) driving an LG ULTRAGEAR at 4K 60 Hz over HDMI showed a brief video dropout. The log showed:

- **No disconnect.** macOS kept the display attached the whole time; the only hotplug events were at boot.
- **Continuous HDMI bit errors:** ~850 "HDMI link status changed" interrupts in 50 minutes (one every 2–3 s), each reporting CED errors on **lane 0** (typically 11) while lanes 1 and 2 were almost always clean.

Errors confined to one lane point to signal integrity somewhere in the cable, the monitor input or the Mac's port. HDMIJester was written to swap one component at a time and watch the numbers change live.

## Install

Requirements: macOS on Apple Silicon (tested on macOS 26.7.1) and Python 3.9+. There are no third-party packages.

```sh
git clone https://github.com/Jason-Vaughan/hdmijester ~/Documents/Projects/hdmijester
ln -s ~/Documents/Projects/hdmijester/bin/hdmijester-watch    ~/bin/hdmijester-watch
ln -s ~/Documents/Projects/hdmijester/bin/hdmijester-snapshot ~/bin/hdmijester-snapshot
```

Admin rights aren't needed. `log show` can read these messages as a normal user.

`hdmijester-watch --version` / `hdmijester-snapshot --version` prints the installed version.

## Use

### Live dashboard

```sh
hdmijester-watch
```

| Area | Meaning |
|---|---|
| **Monitoring via** | Which signal is backing the badge: `CED (HDMI)` once a real error-detection log line has been seen, otherwise `mode/flap poll` |
| **Link** badge | On CED: `CLEAN` (no error reports in the last 60 s), `ERRORS`, `HEAVY ERRORS` (≥10/min). On poll (no CED available): `OK (poll)`, `DEGRADED (poll)` (a mode downgrade or disconnect/flap seen). Both: `DISCONNECTED` |
| Error reports, last 60 s | CED reports seen in the last minute. **0 on a healthy link.** |
| Last CED counts `[L0 L1 L2]` | The latest error count for each TMDS data lane |
| Display health | Per display: best-ever and current resolution/refresh, downgrade count, flap (disconnect) count — tracked even when CED is unavailable |
| Graph | Lane-0 errors per second over the last 60 s (newest on the right) |
| Segments table | One row per test: duration, reports/min, errors/min, average lane-0 count, max per lane, disconnects, "link unstable" reports |
| Events | Disconnects, reconnects, HPD changes, link-unstable reports |

Keys: `n` starts a new labelled test segment (e.g. `cable B, HDMI 2`), `r` resets the current one, `q` quits and prints the summary table. Unplugging and replugging starts a new segment automatically.

Every error event is appended to `captures/hdmijester-watch-<start time>.csv` inside this repo. `captures/` is git-ignored, so evidence stays local.

### Evidence snapshot

```sh
hdmijester-snapshot                 # everything since last boot → captures/hdmijester-snapshot-<time>.txt
hdmijester-snapshot --last 30m      # last 30 minutes
hdmijester-snapshot --since "2026-10-14 19:00:00" -o case-evidence.txt
```

The snapshot contains the hardware and display configuration (serial numbers removed), a per-minute summary table, and every raw link event, ready to attach to a support case.

Everything the tools write goes to `captures/` in the repo, wherever they're run from (the `~/bin` links are resolved back to the repo).

## Testing a display chain

See [docs/TESTING-GUIDE.md](docs/TESTING-GUIDE.md) for a step-by-step test that tells cable, monitor and Mac apart, and for what to bring to Apple.

In short:

| Result | Likely culprit |
|---|---|
| Errors disappear with a different certified cable | The cable |
| Errors on only one monitor input | The monitor |
| Errors follow the Mac's HDMI port across cables and inputs, and the same cable is clean on another computer | **The Mac**: return or warranty |

## How it works

See [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md). Briefly, it polls `log show` for DCP and WindowServer hotplug messages about once a second (`log stream` never delivers DCP messages), de-duplicates them, parses CED, link-status, hotplug, HPD and link-stability lines, and buckets them by **event time** so the graph is accurate even though delivery lags 1–2 s.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The parser tests use real log lines captured from the Mac Studio.

## Limitations

- **Bit-level CED detection requires built-in HDMI.** Over a USB-C→HDMI dongle, dock, or native DisplayPort, the converter chip lives outside the Mac and macOS logs nothing about it. HDMIJester falls back to a coarser signal — tracking each display's resolution/refresh and connect/disconnect flapping from its existing display poll — so it catches a cable bad enough to force a lower mode or drop the link, but not occasional bit errors while the link holds its mode. The **Monitoring via** line always says which signal is active; the badge never shows a bare `CLEAN` implying coverage it doesn't have.
- **Transport is detected by evidence, not guessed.** The badge reads `mode/flap poll` until a real CED/HDMI-link-status log line actually arrives — including on the built-in port, for the first few seconds after launch — then permanently switches to `CED (HDMI)`.
- **Display health is keyed by name.** Two identically-named monitors, or a generic name reused across replugs, won't be told apart.
- **The numbers are only as good as Apple's log messages.** They are undocumented and may change between macOS releases; a format change would silently show `CLEAN`. Confirm with `hdmijester-snapshot` (non-zero raw events) after OS updates.
- **2–3 s latency** because of the polling approach.
- **Built-in displays aren't covered**, and only display slot 1 is tracked for hotplug.

## License

[AGPL-3.0](LICENSE).

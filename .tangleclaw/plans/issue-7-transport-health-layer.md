# Issue #7 — Transport-agnostic health layer (v1, evidence-only)

## Context

HDMIJester currently relies on DCP unified-log messages (CED counts, link-status, hotplug) to judge HDMI link health. That log only exists when the Mac's own display coprocessor drives the HDMI link directly — i.e. the built-in HDMI port on a Mac Studio (`AppleDCPMCDP29XX`/`AppleMCDP29XXUpdateSupport`). The moment a USB-C→HDMI dongle, dock, or native DisplayPort path is used, the converter chip lives outside the Mac and macOS logs **nothing** — confirmed in issue #8's hardware session (dongle/dock showed 0 DCP log lines in 90 min). On those paths HDMIJester's Link badge reads `CLEAN` purely because it never saw an error, which is misleading: it isn't clean, it's blind.

Issue #7 asks for a coarser, transport-agnostic signal — tracking each external display's mode (resolution/refresh) and connect/disconnect flapping via the `system_profiler` poll the tool already runs — so a bad cable/dock still shows *something* even when CED is unreachable, and the UI is honest about which signal is active.

**Scope cut from the issue, verified empirically this session:** issue #7/#8 proposed auto-detecting transport (built-in vs. dongle vs. dock) via `ioreg`'s `{Upstream,Downstream}` properties and converter-class presence (`AppleDCPMCDP29XX`, `AppleDCPAgileCDIDPDisplay`, `AppleDCPDP2HDMI`). Running the actual commands on the Mac Studio (`Mac13,1`, the gold-path machine) showed:
- `ioreg -c <class>` does **not** filter to empty output for a non-matching class — it dumps the full tree regardless (confirmed with a deliberately fake class name producing nearly identical line count to the three cited classes).
- None of the three cited class names exist anywhere in this machine's IORegistry (`ioreg -l`). The real DCP-related kext is `com.apple.driver.AppleMCDP29XXUpdateSupport` (visible only via `kextstat`), and it indicates the chip is present on this Mac at all, not which transport serves a specific connected display.

Guessing an ioreg-based classifier without real fixtures from the dongle/dock hardware risks confidently mislabeling the signal source — worse than the bug this issue is fixing. **Decision (confirmed with the operator): ship v1 using evidence-only signal-source detection — no ioreg.** The badge starts as "poll" on any connection and permanently upgrades to "CED" the instant a real CED/linkchg log line is observed. This is 100% accurate (no guessing), fully testable, and still satisfies the issue's real acceptance bar: never show a bare `CLEAN` that implies more coverage than the tool actually has. Proactive transport auto-detection becomes a follow-up issue once real ioreg fixtures exist from the Air + dongle/dock hardware.

## Implementation

All changes are in `bin/hdmijester-watch` (343 lines today) and `tests/test_parse.py`, following existing conventions exactly: plain functions/classes, no type hints, pure-function/IO-wrapper split (like `_describe_displays()` / `display_mode()`), manual `sys.argv` flag checks (no argparse), stdlib only.

### 1. Per-display structured parsing

Extract the existing regex in `_describe_displays()` into a new pure function returning structured records, then rebuild `_describe_displays()` on top of it so its tested string output is unchanged byte-for-byte:

```python
def _parse_external_displays(sp_output):
    """Parse every external display in `system_profiler SPDisplaysDataType` text
    into records (built-in panel skipped, same rule as `_describe_displays`).
    Each record: {'name', 'resolution', 'hz', 'mode'}; `mode` is an
    (pixels:int, hz:float) tuple for ordering/downgrade comparison, (0, 0.0)
    when unparseable."""

def _describe_displays(sp_output):
    # unchanged signature; now built from _parse_external_displays()
```

### 2. Per-display health tracker

```python
class DisplayHealth:
    """Tracks one external display's mode history across the run.
    best_mode only ever increases, so a cable that fails and later
    'recovers' its original mode still shows the downgrade happened."""
    def __init__(self, name):
        self.name = name
        self.best_mode = (0, 0.0)
        self.current_mode = (0, 0.0)
        self.present = True
        self.downgrades = 0   # current_mode < best_mode, counted each poll it holds
        self.flaps = 0        # present -> absent transitions only (not on return)

def update_health(health, present_by_name):
    """Advance `health` (dict: name -> DisplayHealth, mutated in place) given
    this poll's {name: mode} snapshot from _parse_external_displays(). Returns
    health. Pure given explicit state in/out — no I/O."""
```

Design notes:
- Keyed by display `name` — the only stable identifier available without ioreg node correlation. Two identical-model monitors sharing a name, or a reused generic name across replugs, is a known limitation to document (same spirit as today's "only display slot 1 is tracked").
- Counts are global for the run, not reset by `r`/`n` (unlike `Segment`) — the flap counter's whole purpose is catching reconnects across the session. Document this so users don't expect `r` to clear it.
- Plug in from the existing `poll_mode()` thread (3s cadence) — no new thread needed:
  ```python
  def refresh_mode():
      out = ...  # existing system_profiler call
      displays = _parse_external_displays(out)
      mode['v'] = _describe_displays(out)
      update_health(health, {d['name']: d['mode'] for d in displays})
  ```

### 3. Evidence-only signal source

```python
def signal_source(seen_ced_ever):
    """('ced', 'Monitoring via: CED (HDMI)') once any real CED/linkchg event
    has been observed — permanent once true, it never reverts.
    Otherwise ('poll', 'Monitoring via: mode/flap poll — CED not seen yet')."""

def poll_health_state(display_present, health_records):
    """Badge severity when CED isn't available: 'disconnected' | 'ok' | 'degraded'.
    'degraded' fires on any downgrade or flap seen so far. No 'heavy' tier —
    poll fidelity is coarse by design; that's an honest limitation, not a gap."""
```

In the event-drain loop in `main()`, two one-line additions set the proof flag permanently:
```python
if kind == 'ced':
    ...
    transport['ever_ced'] = True
elif kind == 'linkchg':
    ...
    transport['ever_ced'] = True
```

Badge selection branches on the signal source instead of always calling `link_state()`:
```python
src_key, src_label = signal_source(transport['ever_ced'])
if src_key == 'ced':
    status = badge[link_state(connected, mode['v'] != NO_EXTERNAL, rate)]   # unchanged
else:
    status = poll_badge[poll_health_state(mode['v'] != NO_EXTERNAL, health.values())]
```

`link_state()` and its 4 existing tests are untouched — zero risk to the built-in-HDMI/CED path, which keeps behaving exactly as today.

### 4. UI placement

Curses row numbers in `main()`'s draw block are hard-coded (`put(8,...)`, `put(12,...)`, and the `rows = segs[...]` / `y = 15 + len(rows)` constants). Plan:
- `src_label` goes on the currently-blank row 1 (between the header and the `Link:` row) — free, no shift needed.
- A new "Display health" row (comma-joined, same join style as `_describe_displays`, e.g. `LG ULTRAGEAR: 3840x2160@60Hz (best same) dg:0 fl:0`) is inserted after row 6 ("This segment"). Every row number from there down (`put(8,...)` through the `15 + len(rows)` Events offset) shifts down by 1, including the `H - 26` Segments-table-height constant, to avoid collision on short terminals. Treat this as a careful, test-with-real-terminal step during implementation, not a guess made now.

### 5. Tests (`tests/test_parse.py`, following existing hand-fixture convention)

- `ParseExternalDisplaysTests` — reuse `SP_ONE_EXTERNAL`/`SP_TWO_EXTERNAL`, assert `mode` tuples; add a `SP_DOWNGRADE` fixture (e.g. 1080p30) for ordering checks.
- `DisplayHealthTests` (`update_health`): `test_first_poll_establishes_baseline`, `test_mode_drop_counts_one_downgrade`, `test_oscillation_counts_each_drop`, `test_disappearance_counts_a_flap`, `test_reappearance_does_not_double_count_flap`, `test_two_displays_tracked_independently`.
- `SignalSourceTests`: `test_poll_label_before_any_ced_evidence`, `test_ced_confirmed_once_real_event_seen`, `test_ced_label_is_permanent_once_set` (feed `False` after `True` and confirm it stays `'ced'` — guard against regressions since this must never revert).
- `PollHealthStateTests` — mirrors `LinkStateTests` style for `'ok'`/`'degraded'`/`'disconnected'`.

### 6. Docs

**README.md**
- "Use" table: add `Monitoring via` and `Display health` rows. Note the Link badge now has two vocabularies: `CLEAN/ERRORS/HEAVY ERRORS` (CED) vs `OK (poll)/DEGRADED (poll)` (poll-only), with `DISCONNECTED` common to both.
- "Limitations": rewrite the "HDMI only" bullet — bit-level CED still requires built-in HDMI; over any external-converter path HDMIJester now reports a coarser mode-downgrade/flap signal instead of nothing (catches a cable bad enough to force a lower mode or drop the link, not occasional bit errors while holding mode), and always labels which signal is active instead of a bare `CLEAN`. Note transport is detected by evidence (did a CED event ever arrive), not guessed — so it may read "poll" for the first several seconds even on the built-in port until the first log line arrives.

**docs/HOW-IT-WORKS.md**
- New "## Health signal tiers" section: a table (CED gold / mode+flap poll), explains the evidence-only upgrade rule (`ever_ced` is sticky — once true, always true), and the `DisplayHealth` model advancing on the existing ~3s `system_profiler` poll. Explicitly note that proactive transport auto-detection (ioreg-based) was investigated and deferred — the class names issue #7/#8 cite aren't real `ioreg -c`-matchable classes (verified on the Mac Studio), so it needs real fixtures from dongle/dock hardware before it can be built safely; filed as a follow-up issue.

**CHANGELOG.md** — `### Added` under `[Unreleased]`:
> Transport-agnostic health layer: when CED can't reach macOS (USB-C→HDMI dongle/dock, native DisplayPort), `hdmijester-watch` tracks each external display's best-seen and current mode and flap/downgrade counts from the existing `system_profiler` poll, labels which signal is active (`Monitoring via: CED (HDMI)` vs `mode/flap poll`), and never shows a bare `CLEAN`/`OK` badge implying coverage it doesn't have. Built-in HDMI's CED behavior is unchanged. (#7)

### 7. Follow-up issue to file (not part of this chunk)

`[feature] Auto-detect HDMI transport (built-in vs. dongle/dock) via ioreg` — records today's finding (cited class names aren't real `ioreg -c` matches; `ioreg -c` doesn't filter to empty for non-matches) as the reason it was deferred, and asks for real ioreg dumps from the Air + dongle/dock hardware before design.

## Verification

- `python3 -m unittest discover -s tests -v` — all existing tests stay green; new tests above pass.
- Manual smoke test on this Mac Studio with the LG monitor on built-in HDMI: confirm badge starts `Monitoring via: mode/flap poll` immediately on launch, flips to `Monitoring via: CED (HDMI)` within a few seconds once the first log line arrives, and stays flipped.
- Manual check of the shifted curses row numbers in a real terminal (`hdmijester-watch`), including a short terminal (resize small) to confirm the Segments/Events layout doesn't collide.

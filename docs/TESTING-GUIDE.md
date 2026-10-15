# Testing a display chain (cable vs monitor vs Mac)

Goal: change **one** component at a time and let the numbers decide.

## Before you start

- Close nothing; normal desktop use is fine.
- Note the display mode. 4K 60 Hz over HDMI runs at the HDMI 2.0 maximum (594 MHz pixel clock, 18 Gbps) and is the most demanding case. Keep it the same across tests.
- Have at least one **certified** cable: "Premium High Speed" (18 Gbps, has a QR/hologram label) or "Ultra High Speed" (48 Gbps). Unlabelled cables often fail at 4K60.
- Run `hdmi-watch` in Terminal.

## Procedure

Give each step at least **2 minutes** (the baseline here produced 15–35 reports/min, so 2 minutes gives a clear signal). Press `n` and label each step.

| # | Label | Change |
|---|---|---|
| 1 | `baseline` | Current setup, untouched |
| 2 | `cable B` | Swap to a certified cable, same ports |
| 3 | `cable B, LG HDMI 2` | Same cable, different monitor input |
| 4 | `orig cable, LG HDMI 2` | Original cable on the other input |
| 5 | `USB-C to DP` | USB-C/Thunderbolt → DisplayPort, bypassing the Mac's HDMI port. CED counts don't apply; watch for disconnects |
| 6 | `cable B on other computer` | Optional: same monitor and cable on another computer. HDMI-Watch can't measure this, so just watch for dropouts |

Press `q` at the end. The summary table is printed and the CSV is in `captures/`.

## Reading the results

| Pattern | Conclusion |
|---|---|
| Step 2 drops to ~0 reports/min | **Bad or under-spec cable.** Keep the certified cable. |
| Errors only on one LG input (steps 3/4 clean, 1 dirty) | **Monitor input.** Use another input or contact LG. |
| Errors in every HDMI combination, step 5 stable, and the same cable and monitor fine elsewhere | **The Mac's HDMI port.** Return or warranty. |
| Errors everywhere *including* other computers | **The monitor.** |
| Only lane 0 errors (lanes 1–2 clean) | Typical of one marginal conductor or contact: cable or connector. Doesn't identify which end on its own; the swaps above do. |

## Evidence for Apple / the retailer

1. Run `hdmi-snapshot` and attach the file it saves in `captures/`. It has the hardware model, display mode, per-minute error table and raw log lines.
2. Attach the `hdmi-watch-*.csv` and a screenshot of the segments table showing the comparison.
3. Run **Apple Diagnostics**: shut down, hold the power button until "Loading startup options" appears, then press **Cmd+D**. Write down the reference code. It doesn't specifically test the HDMI port, so a clean result doesn't clear it, but support asks for it.
4. Check the model against the receipt: `system_profiler SPHardwareDataType | grep 'Model Identifier'` (`Mac13,1` is the 2022 M1 Max/Ultra Mac Studio).

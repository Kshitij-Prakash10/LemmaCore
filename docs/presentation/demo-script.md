# Demo script (slide 5, 60 seconds, then back to slides)

Built from `failover/app/static/index.html` and `app.js` on main at 74fb206, and from the `CONTEXT.md` section 7 plan. Reference numbers come from `demo_outputs/coverage.json` (core 0.1, seed 1) and `models/metrics.json`. **Always read numbers off the screen.** The app runs the scenario live, and its settings (15 km to the station) differ from the harness cells (12 km), so the minutes can differ slightly from the harness.

## Before the pitch (15:30 to 15:45)

1. On the presenting laptop: `make app` (or `python -m failover.app.server`), then open http://127.0.0.1:5000.
2. **Turn Wi-Fi off** and reload. Everything must still load (no CDN).
3. Check the badge next to the title. It must **not** say "STUB core". If it does, the real core did not import: stop and tell the builders.
4. Open each tab once: Advisor, Coverage map, Real data, Assumptions, Report.
5. Leave the app on the **Coverage map** tab. Keep the slides in a second window and switch with Alt+Tab.

## Click by click

| # | Click | Say (short) | What the screen should show |
|---|---|---|---|
| 1 | **Coverage map** tab | "Every single and double fault, in four conditions. Left: no advisor. Right: with the advisor." | Two grids. Baseline has red (UNSAFE) cells in the two climb columns; the advisor grid has none. Header: 44 vs 0. |
| 2 | Click a **red baseline cell** in the hot-climb column, row STANDBY_STUCK (or U1_TRIP + STANDBY_STUCK) | "Hot day, climbing, unit 1 trips and the standby does not take over." | The Advisor tab opens with those faults set. |
| 3 | **Run advisor** | "Without help the motor overheats while the train is moving. The advisor says: at least N minutes, heat is the limit, stop at the next safe place." | Decision card: STOP_AT_NEXT, limiting factor heat, a p5 figure (harness cell: 6.3 min, nominal 8.8). Temperature chart: baseline crosses the limit, advisor stays under. |
| 4 | **Auto-diagnose** | "The pilot does not need to know which unit failed. The classifier reads the noisy sensors and names the fault. Below 60 percent confidence the advisor ignores it and uses the cautious path." | "Diagnosis: ... (confidence N%)". Expect "unit 1 lost" type faults. It may say STANDBY_STUCK or MCB_TRIP: they look identical in the signals, and the advisor treats them the same. |
| 5 | **Stick the temperature sensor**, then **Run advisor** | "Now the wrong-data case. The temperature reading freezes while the model says the motor is heating. The advisor flags it, drops its confidence and assumes the worst." | Flag `temp_sensors_disagree`, confidence low, decision moves to **STOP_NOW** (harness cell STANDBY_STUCK + TEMP_SENSOR_STUCK, hot climb: p5 0.4 min). |
| 6 | **Assumptions** tab (5 seconds) | "Every value is tagged assumed or confirmed. Only the air-leak rate has a public source so far." | Table with status badges. |

Then press **Unstick the temperature sensor** (so the next run is clean) and go back to the slides.

## If something fails

| Problem | Fallback |
|---|---|
| The app does not start | Open `demo_outputs/report.html` in the browser (static file, offline) and show the coverage table. Say: "Here is the same proof as a static report." |
| Badge says STUB core | Do not demo advice numbers. Show `demo_outputs/report.html` and slide 5's numbers. |
| Clicking a cell does nothing | Press **Hard case: hot climb, U1 trips, standby stuck** (sets U1_TRIP + STANDBY_STUCK, 45 C, 2.7 %, 15 km), then **Run advisor**. |
| Auto-diagnose names the wrong fault | Say it straight: "It is trained on our simulator. On held-out scenarios it gets the exact fault set right about 55 percent of the time after a fault, and the advisor only trusts it above 60 percent confidence." |
| Real data tab is empty | Skip it. The MetroPT-3 leak fit and anomaly detector were not built at 14:53. Do not mention a real-data result. |
| Laptop dies | Present from the PPT. Slide 5 has the numbers. |

## Do not say

- "The advisor sheds loads to save the train." In the hard case it sheds nothing; the stop decision saves it.
- Any MetroPT-3 result, unless the Real data tab shows one.
- "Proven safe." Say "in our model, with assumed values".

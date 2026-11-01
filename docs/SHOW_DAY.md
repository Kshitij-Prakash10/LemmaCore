# Show-day runbook (Agent A, 15:24)

Presentations start 16:00. Five minutes of pitch, three of questions. The software must run offline on the laptop.

## Before you walk on (do this at 15:45, on the presenting laptop)

1. Open a terminal in the repo folder and run:
   ```bash
   . .venv/bin/activate
   python -m failover.app.server
   ```
2. Open http://127.0.0.1:5000. The badge in the header must say "simulation core 0.1" and not "stub".
3. Turn Wi-Fi off. Reload the page. It must still work. (No CDN, no cloud calls. A test asserts this.)
4. Press Hard case on the Advisor tab. Expect: STOP NOW, at least 5.5 minutes, typical 7.8, limit motor heat, without the advisor Unsafe, with the advisor Stopped in time.
5. Leave the browser on the Advisor tab with the hard case showing. Close other tabs and notifications.
6. Keep `demo_outputs/report.html` open in a second tab. It is the static fallback.

If `.venv` is missing: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`.
If the models are missing: `make train` (needs `data/raw`; the trained models are committed in `models/`, so this should not be needed).

## Click path (5 minutes)

| Time | Tab and click | Say |
|---|---|---|
| 0:00 | Guide | The problem in one sentence: the second converter does not always take over, and the loco pilot has no tool for that moment. |
| 0:40 | Advisor, Hard case | One screen, one decision. Point at "at least 5.5 minutes" (cautious end, 5th percentile), "motor heat", "Already without power". |
| 1:40 | Same screen, outcomes table and chart | Without the advisor: unsafe. With it: stopped in time. Red line crosses the limit, dark line stays under. |
| 2:10 | Freeze the temperature sensor | A dead sensor makes the advisor assume the worst. Low confidence, at least 0.4 minutes. |
| 2:40 | Coverage map | 144 tests per policy. 44 unsafe without the advisor, 0 with it. 8 stops that were not needed. Click a red square to open it in the Advisor. |
| 3:40 | Assumptions | Every loco number is an assumption. We tested 32 combinations of the five most uncertain values: advisor unsafe in none. |
| 4:10 | Real data | Compressor data from a metro train, a proxy. Leak fitted at about 0.09 bar/min. |
| 4:40 | Close | Next step: real fault codes in; the same test as an acceptance test for new converter software. |

Skip Auto-diagnose on the hard case. It returns no fault at 0.65 confidence there. If a judge asks for it, use a single-fault case and state the classifier accuracy honestly.

## Numbers you may quote

- 144 tests per policy (36 fault combinations, 4 conditions). Baseline unsafe 44. Advisor unsafe 0. Unneeded stops 8. Safety checks failed 0.
- Robustness: 32 corners, advisor unsafe in 0 of them. Baseline unsafe ranged 0 to 44; unneeded stops 8 to 52.
- Most sensitive assumptions: motor trip temperature and brake-air minimum.
- Classifier, unseen scenarios: whole set exactly right 66 %, faults found 73 %, calls right 81 %. On fault pairs it never saw: 51 % exact. A compressor fault combined with a converter trip is almost never found.
- Real data: 9,522 stretches. Anomaly detector at its pre-set threshold caught 0 of 4 leaks; looser settings 3 of 4 at 0.17 false alarms per day. The optional leak flag stays silent in the demo.

## Say these limits before a judge does

1. Every loco number is an assumption. No railway expert confirmed any of them (motor trip temperature, brake-air minimum, load kW and the safe-stop distance are the ones that matter most).
2. The tests run on a simulation of our model, not on a real loco.
3. In the 144-test run the advisor is told the true faults. Auto-diagnose is right about two times in three on a whole fault set.
4. "Stop at the nearest safe place" assumes a safe place about 3 km ahead.
5. The real-data check is a metro compressor, a proxy.
6. Conventional 2-converter locos only. 3-phase locos slow their blowers; not modelled.
7. Decision support, not a certified safety system.

## Likely questions

- Does this already exist? Fault codes and standby converters exist. A tested decision for the failed-standby case, with a harness that proves every single and double fault, is what we add.
- Why trust the numbers? We do not. They are labelled assumed, and we show that the safety result holds across 32 corners of the uncertain values.
- Why does the advisor stop at 8 cases where it did not need to? It is cautious on purpose. A stop costs minutes; a missed stop costs the loco.
- Is the ML needed? The advisor works from the true or assumed fault. The classifier supplies the fault when it is not known, and we report its accuracy as it is.

## If something breaks

| Symptom | Fix |
|---|---|
| Page does not load | Look at the server window. Restart `python -m failover.app.server`. Port busy: `lsof -ti :5000 | xargs kill`, then restart. |
| A run hangs | Press Hard case again. It takes about a second. |
| Badge says stub | Wrong folder or old process. Kill the server and start it again from the repo root. |
| Total failure | Show `demo_outputs/report.html` and the screenshots in the slides. Talk through the same click path. |

## AI and open-source disclosure (say it once)

Code written with Claude Code: Agent A (core, harness, app interface) Claude Sonnet 5.5; Agent B (ML and app backend) Claude Opus 5.5; a third Claude helped with the presentation notes and slides. Packages: numpy, scipy, pandas, scikit-learn, joblib, Flask, pytest. Real data: MetroPT-3 (UCI, CC BY 4.0).

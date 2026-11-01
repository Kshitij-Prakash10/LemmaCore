# App guide: understand it and present it (Agent A, 15:25)

Run the app: `python -m failover.app.server`, then open http://127.0.0.1:5000. It works with Wi-Fi off. Each tab has its own link (`#guide`, `#advisor`, `#coverage`, `#realdata`, `#assumptions`, `#report`).

## The one-sentence idea
When a loco's auxiliary converter fails and the backup does not take over, the app tells the loco pilot what to do next, and proves that advice by testing every fault.

## Tab by tab

| Tab | What it shows | What to say |
|---|---|---|
| **Guide** | The problem, how to use the app, how to read the answer, the words used. | "This is the plain-words page, so anyone can follow the demo." |
| **Advisor** | You pick up to two faults and the conditions. It returns one decision, the minutes left, what to switch off, what is already dark, and two charts. | "One screen, one decision. Here is the hard case." |
| **Coverage map** | All 144 tests (36 fault combinations in 4 conditions), without the advisor and with it. Click a square to open that test in the Advisor. | "Every fault tested. Red is unsafe. The advisor column has no red." |
| **Real data** | The brake-air leak fitted from real compressor data, and an anomaly detector tested on months it had not seen. | "We also checked our methods on real data. It is a metro train, so it is a proxy." |
| **Assumptions** | Every loco number with an assumed or confirmed badge and its source. | "None of these are confirmed yet. We show them so nothing is hidden." |
| **Report** | The downloadable test report, and the classifier's accuracy table. | "Here is how well the fault classifier works, on data it did not see." |

## The five-minute demo, click by click
1. **Guide tab, 20 s.** Read the first paragraph aloud. "Many locos have a second converter. Sheds report it does not always take over."
2. **Advisor tab, press "Hard case", 60 s.** The card turns to red words, for example "Stop now and call for help". Point to: minutes left (a cautious figure), what limits it (motor heat), "Already without power" (what the failed converter took with it), and the table "Without the advisor: Unsafe, with the advisor: Stopped in time". Point at the chart: the red line crosses the dashed limit, the dark line stays under.
3. **Press "Freeze the temperature sensor", 30 s.** The wrong-data case. The advisor notices a frozen reading and assumes the worst. "Even a dead sensor does not make it unsafe."
4. **Press "Auto-diagnose from sensors", 30 s.** The classifier names the faults from sensor readings. Say its accuracy honestly (see the numbers below).
5. **Coverage map, 60 s.** "44 of 144 tests are unsafe without the advisor and 0 with it." Click a red square in the left grid and watch it open in the Advisor.
6. **Assumptions, 20 s.** "Every loco number is an assumption until a railway expert confirms it, and we tested what happens if we are wrong."
7. **Close, 30 s.** Future scope: real fault codes in, and the same test as an acceptance test for new converter software.

## Numbers you may quote (all from files in the repo)
- Tests: 144 per policy. Baseline unsafe 44. Advisor unsafe 0. Stops that were not needed 8. Safety checks failed 0. (`demo_outputs/coverage.json`)
- Robustness: across 32 combinations of the five most uncertain values, the advisor was unsafe in none (`demo_outputs/robustness.json`). Without the advisor the unsafe count ranged from 0 to 44. Stops that were not needed ranged from 8 to 52.
- Most sensitive assumptions: the motor trip temperature and the brake-air minimum (`demo_outputs/sensitivity.json`).
- Classifier on unseen scenarios (`models/metrics.json`): whole fault set exactly right in 66%, faults found 73%, calls that were right 81%. On fault pairs it never saw, 51% exact. A compressor fault combined with a converter trip was almost never found. Say that.
- Real data: leak fitted at about 0.09 bar/min from 9,522 stretches. The anomaly detector with its pre-set threshold caught 0 of 4 labelled leaks. With looser alarm settings it caught 3 of 4, at 0.17 false alarms a day.

## What the words on the answer card mean
- **Minutes left, "at least N":** the cautious end (5th percentile) of the time until the first limit: motor heat, brake air or battery. The real time is usually longer.
- **What limits it:** which of those three limits comes first.
- **Switch off:** loads the crew should turn off to stretch the time. Often "nothing".
- **Already without power:** loads that stopped because the converter failed. They are the cause of the danger, and the crew cannot choose to switch them off.
- **Keep on:** loads that still run, including the essentials.
- **How sure:** high, or low when the advisor does not trust the sensor or had to guess the faults.

## Limits to say aloud
1. Every loco number is an assumption, not confirmed by a railway expert.
2. The tests run on a simulation of our model, not on a real loco.
3. The advisor is told the true faults in the 144-test run. Auto-diagnose uses the classifier, which is right about two times in three on a whole fault set.
4. The "stop at the nearest safe place" advice assumes a safe place about 3 km ahead.
5. The real-data check uses a metro train compressor, a proxy.
6. The model covers conventional 2-converter locos. 3-phase locos slow their blowers instead of dropping loads, which we did not model.
7. This is decision support, not a certified safety system.

## If something breaks during the demo
- The page does not load: check the server window, restart with `python -m failover.app.server`.
- A run hangs: press the hard-case button again. The advisor takes about a second.
- Total failure: show `demo_outputs/report.html` (a static page with the same coverage grid) and the screenshots in the slides.

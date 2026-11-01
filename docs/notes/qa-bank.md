# Q&A bank: AuxiCompass (judge questions, short honest answers)

Updated 16:30 from main at a99c74d: `demo_outputs/coverage.json`, `robustness.json`, `sensitivity.json`, `models/metrics.json`, `anomaly_metrics.json`, `leak_metrics.json`, `docs/model.md`, `docs/ml.md`, `docs/SHOW_DAY.md`, `docs/public_answers.md`. Answer in your own words; these are the facts to hit. **Bold** is the one line to remember.

## Numbers to know cold

| What | Value | Source |
|---|---|---|
| Harness runs | 8 faults, 36 combinations, 4 conditions, 144 per policy, 288 total, about 1.3 s | coverage.json |
| Baseline unsafe / advisor unsafe | **44 / 0 of 144** | coverage.json |
| Stops the baseline did not need | 8 | coverage.json |
| Safety properties failed | 0 | coverage.json |
| Robustness | 32 assumption corners, 4,608 runs per policy, **advisor unsafe 0 in every corner**; baseline unsafe 0 to 44 | robustness.json |
| Live app, Hard case button | **STOP NOW, at least 5.5 min, typical 7.8, limit motor heat** (15 km, fault seen at 120 s) | SHOW_DAY.md |
| Slide 5 harness hard case | at least 6.3 min, nominal 8.8, stop at next safe place (12 km) | coverage.json |
| Live app, frozen temperature sensor | at least 0.4 min, confidence low, flag `temp_sensors_disagree` | SHOW_DAY.md |
| Classifier, held out | exact fault set 66% (55% counting only post-fault windows), precision 0.81, recall 0.73; stuck sensor 1.0 / 1.0; unseen pairs 51% exact | metrics.json |
| Real data (MetroPT-3) | 9,522 compressor-off stretches, leak decay median 0.091 bar/min; anomaly detector 0 of 4 leaks at the pre-set threshold, 3 of 4 at a looser one with 0.17 false alarms per day | ml.md |
| RDSO | 582 failures, 2,116 units, FY 2024-25, about 27 per 100 a year (our arithmetic), conventional locos | CONTEXT.md |

**If a judge compares slide 5 with the screen:** "The slide is the harness case at 12 km; the screen is the live case at 15 km with the fault seen later. Both say the same thing: not enough time to reach the station, so stop."

---

## A. Problem selection (20)

1. **Why this problem?** BLW asked "if this component fails during a journey, what should the system do next?" RDSO's own minutes show the auxiliary converter fails often and the standby sometimes does not take over. **One user, one moment: the loco pilot, mid-section, after the standby fails.**
2. **Is 27 per 100 RDSO's figure?** No. It is our sum of their FY 2024-25 table: 582 failures in 2,116 units. Conventional electric locos only.
3. **Doesn't the loco protect itself already?** Yes, it derates and trips the motor. That protects the motor, not the train: it does not tell the crew what to switch off or whether to stop. Our baseline includes that protection and is still unsafe in 44 of 144 cases.
4. **Who uses it?** The loco pilot and assistant on the cab screen. RDSO and shed electricians would use the harness as an acceptance test.
5. **Why the name AuxiCompass?** It guides the crew through an auxiliary supply failure. It is decision support, not a safety system, so we avoided names like "guard".

## B. Understanding of the problem (15)

6. **Root cause?** The changeover to the standby is unreliable (Siemens 2x130 kVA after a fault; Medha 2x130 kVA when the front-panel MCB trips), and the fault log keeps 20 days while sheds see the loco every 60, so evidence is lost. Makers did not share root-cause analyses.
7. **What exists today?** REMMLOT remote monitoring (health to the shed), CLW's analytics spec for 3-phase locos (deployment unknown), the loco's own thermal protection. **We found no crew-side advisor; we say "found none", not "none exists".**
8. **What does a failure cost?** One news report: an auxiliary converter fault left three Vande Bharat coaches without AC and lights for about an hour (2019). We have no cost-per-failure figure and did not invent one.
9. **What does the crew do today?** We found an old rule (try to resume within 20 minutes, else inform control) and a 3-phase handbook line "if anything is abnormal, fail the loco". No specific procedure for this fault.

## C. Idea and innovation (20)

10. **What is new?** A crew-facing decision (what to switch off, at least how many minutes, continue or stop) **plus a fault-injection harness that proves it against every single and double fault**. The harness is also a reusable acceptance test.
11. **Why physics, not just ML?** There is no real failure data for this loco. Physics gives limits we can explain and test. ML only names the fault, and a learned estimate may lower the minutes left, never raise them.
12. **What did you leave out?** Failure prediction (no data), passenger features, cloud (the loco runs offline), any safety-certification claim.
13. **Why "at least N minutes" and not an average?** The pilot needs a figure that is rarely too high. We report the 5th percentile over 200 random parameter draws.

## D. Solution design and the hard case (15)

14. **The hard case?** Hot day, 1-in-37 climb, unit 1 trips, standby stuck. Without the advisor the motor reaches its trip limit while moving. With it: STOP NOW (live app) or stop at the next safe place (harness), no limit hit.
15. **Second hard case, wrong data?** The temperature sensor freezes. If the reading is exactly flat for 8 samples while the model says it should change by more than 0.05 C/s, the advisor flags `temp_sensors_disagree`, lowers confidence and assumes the motor is 5 C below its trip. In the live app that drops the estimate to at least 0.4 minutes.
16. **Does the advisor ever make things worse?** Never unsafe in our runs. It made 8 unneeded stops (6 with a dead sensor and a heating motor, 2 from the cautious 5th percentile). **A stop costs minutes; a missed stop costs the loco.**
17. **What counts as unsafe?** A limit hit while moving: motor temperature, brake air below its minimum, or battery empty. A controlled stop before any limit is not unsafe.
18. **Is 0 unsafe too good to be true?** It is our model with assumed values, and in the harness the advisor is told the true faults. We also stress-tested it: 32 corners of the five most uncertain values, advisor unsafe 0 in all of them.
19. **Why do only climbs fail, and why does a hot day give the same count?** Heat on the flat is half that on a climb, so on the flat the motor never reaches its trip within 30 minutes. Ambient changes **when** it trips, not **whether**: hot climb at about 13.6 min into the run, cool climb at about 17.1 min, both before the station (18 min away). So both climbs give 22 unsafe and both flats give 0.
20. **Why does the advisor shed nothing in the hard case?** With unit 1 lost and no takeover, its loads are already dark. Switching off more does not cool the motors, so the decision that saves it is the stop. In other cases it searches all 128 load subsets.

## E. Working prototype (10)

21. **Does it run offline?** Yes. Flask plus plain HTML, CSS and JavaScript, no CDN, no cloud, no model downloads. An app test runs with the network blocked.
22. **How do I reproduce your numbers?** `make harness` (about 1.3 s) writes coverage.json; `python -m failover.core.robustness` (about 35 s) writes robustness.json; `make train` retrains the classifier. Every random process takes a seed.
23. **What is on screen?** Tabs: Guide, Advisor (decision card, minutes, limit, switch off or keep on, chart of baseline vs advisor), Coverage map (click a cell to open the case), Assumptions (every value tagged), Real data, Report.

---

## F. Technical: physics model

24. **Heat model?** One thermal node for the traction motors: `C dT/dt = Q - h (T - T_amb)`. C 300 to 500 kJ/K; h 1.2 to 2.0 kW/K with the blower on and 12 to 20% of that with it off; Q is heat at full load (70 to 110 kW) times a factor for gradient and load, zero when stopped. Start 40 C above ambient. Trip 180 C (assumed).
25. **How do you get minutes left fast?** A closed form for constant Q: `t = -(C/h) ln((T_lim - T_ss)/(T0 - T_ss))`, with `T_ss = T_amb + Q/h`. A test checks it against step-by-step simulation within 1%.
26. **Converter model?** Each unit gives `kVA x power factor (0.8) x ambient derate` kW (derate from 1.0 at 40 C down to 0.8 at 48 C). Loads have a home unit; if failover works, an orphaned load moves to the unit with the most spare capacity; if not, it goes dark.
27. **Brake air?** `dP/dt = fill x compressor_on - leak` in bar/min, capped at normal pressure. The leak rate (0.04 to 0.10 bar/min) is our one sourced value, from Patiala Locomotive Works dispatch test sheets. The advisor keeps an extra 0.5 bar reserve.
28. **Battery?** State of charge falls only when the control and charger load is dark: control current over usable capacity.
29. **Loco protection in the baseline?** Halves the heat within 10 C of the trip, then trips at the limit. That is our stated modelling assumption for "no advisor".
30. **Known limits of the model?** One thermal node; a derated loco is not slowed; converter temperature is derived; 3-phase load sharing at about 37 Hz is not modelled.

## G. Technical: the advisor algorithm

31. **How does it choose what to switch off?** It tries all 2^7 = 128 subsets of the 7 loads, keeps those the healthy units can actually power, then prefers more essential loads, then more minutes to the first limit, then more load kept.
32. **How is the decision made?** Continue if the station time is within 0.8 of the p5 minutes; else stop at the nearest safe place (assumed 3 km) if that fits within 0.8; else stop now. 0.8 is a safety factor we chose, not a railway rule.
33. **What is the weakest assumption in the decision?** **The 3 km to a safe stopping place.** If the nearest loop or halt is further than the minutes allow, the advisor can be unsafe. We say this before they ask.
34. **Speed?** `advise()` under 50 ms; one 30-minute simulation under 0.5 s.
35. **What if the advisor's estimate is optimistic?** In the robustness run, when the real loco is worse than assumed (trip 160 C, heat 110 kW, brake minimum 7 bar), the minutes-left figure was optimistic in up to 100 of 144 cases. The decision stayed safe because it stops early. That is why we show "at least" and a confidence flag, and why the trip temperature is the first value to confirm.

## H. Technical: harness, sensitivity and robustness

36. **What does the harness check in every run?** Four properties: brake air above minimum, essential loads kept, no more load than available power, minutes left never optimistic against the model's own truth. 0 failed.
37. **What is the oracle caveat?** In the 144-run harness the advisor is given the true fault set. In the app it gets the classifier's answer only above 60% confidence, otherwise it infers from signals.
38. **Sensitivity?** Each assumed value moved by 20% one at a time. Hard case: motor trip temperature swings minutes left from 4.9 to 13.3 (8.4 min), heat at full load 5.1, heat capacity 3.5. Failed compressor: brake-air minimum 48.0, leak 24.9.
39. **Robustness?** All 32 combinations of low and high values of five uncertain parameters (trip 160/200 C, heat 70/110 kW, blower-off cooling 0.12/0.20, brake minimum 5/7 bar, leak 0.04/0.10). The real plant uses the corner; the advisor keeps its beliefs. **Advisor unsafe 0 in all 32 corners (4,608 runs).** Baseline unsafe 0 to 44, unneeded stops 8 to 52.

## I. Technical: machine learning

40. **What does the classifier do?** Names which of the 8 faults are present from a 60 s window of observed (noisy) signals, so the pilot need not know which unit failed.
41. **Training data?** Generated by our core, never separate physics: 37 fault sets (healthy, 8 singles, 28 pairs) x 40 random scenarios, ambient 20 to 48 C, gradient 0 to 3%, load, 2 or 3 units, noise 0 to 0.1, and plus or minus 20% on five physics values (domain randomization). 4,224 training windows.
42. **Model and why?** One gradient-boosting classifier per fault (scikit-learn HistGradientBoosting, binary relevance). A single joint random forest found 0 of 4 unseen fault pairs; one model per fault found 2 of 4. About 14 ms per prediction.
43. **How did you avoid leakage?** Split by scenario seed, not by row; 4 whole fault pairs never seen in training; a test fails if seeds leak or the model's core version differs from the code.
44. **Results?** Exact fault set 66% on held-out seeds (55% counting only windows after the fault), precision 0.81, recall 0.73. Stuck sensor 1.0 / 1.0. Accuracy 0.71 at no noise, 0.63 at the highest noise, 0.69 with parameters outside the training range.
45. **Why so low on some faults?** STANDBY_STUCK, MCB_TRIP and U1_TRIP plus STANDBY_STUCK all mean "unit 1 lost, loads not moved", so the signals are identical; no model can separate them, and the advisor treats them the same. COMPRESSOR_FAIL is missed early because pressure has barely moved. A compressor fault combined with a converter trip is almost never found.
46. **Why not press Auto-diagnose on the hard case?** On that case it returns "no fault" at 0.65 confidence. Use a single-fault case, or explain it honestly with the numbers above.
47. **Isn't it just learning your simulator?** Yes, and we say so. It shows how well we can invert our model, not how it does on a real loco. Real use needs retraining on real fault logs.

## J. Technical: real data (MetroPT-3)

48. **What is it?** Real sensor data from a metro train's air compressor in Porto (UCI, CC BY 4.0), with four maintenance-confirmed air leaks. **A proxy, not an Indian loco.**
49. **What did you fit?** 9,522 compressor-off stretches: reservoir decay median 0.091 bar/min (95% interval 0.0908 to 0.0921). It includes normal air use, so it overstates pure leakage; it is above the loco dispatch limit (0.067), which fits that reading. The core does not use it by default.
50. **Anomaly detector?** Isolation Forest trained on February 2020, threshold set on March, tested from April (153 days). **At the threshold fixed in advance it caught 0 of 4 leaks.** At a looser pre-set threshold, 3 of 4 with 0.17 false alarms per day. The score does separate leak from normal (median 0.69 vs 0.49).
51. **The supervised leak flag?** Random forest trained on leaks 1 to 3, tested on leak 4: recall 0, so it stays silent in the demo. We report it rather than hide it.

## K. Software and process

52. **Architecture?** `failover/core` (physics, advisor, harness), `failover/ml` (classifier, real data), `failover/app` (Flask and static pages). A written contract (`CONTRACT.md`) fixes the types and function signatures between them.
53. **Testing?** pytest suites for core (contract shapes, determinism, closed form vs stepping, hard case, robustness), ML (no leakage, version match, speed) and app (every endpoint returns valid JSON, offline with the network blocked).
54. **Determinism?** Every random process takes a seed (harness seed 1, classifier seed 7, anomaly seed 13), so a stranger gets the same numbers with one command.
55. **How did two agents work in parallel?** Disjoint file ownership, a versioned contract, and requests as new files in `docs/requests/`, so merges never conflicted.

## L. Ownership and disclosure

56. **What was AI and what was you?** Code was written with Claude Code: Agent A (core, harness, app interface) Claude Sonnet 5.5, Agent B (ML and app backend) Claude Opus 5.5, and a third Claude helped with the presentation notes and slides. **The running tool contains no language model.** We chose the problem, the scope and the assumptions, and we checked the results. (Each member: say your own part here.)
57. **Open source used?** Python, numpy, scipy, pandas, scikit-learn, joblib, Flask, pytest; MetroPT-3 data.

## M. Future scope and impact (10)

58. **Path to real use?** Put in the makers' real fault codes; give RDSO the harness as an acceptance test for changeover software; model BLW's 3-phase locos (three converters sharing load at about 37 Hz); keep 60 days of fault log, not 20.
59. **Who adopts it, what does it need?** RDSO for the test, zonal sheds and crews for the advisor. It needs maker fault codes, shed data, confirmed loco values, the real distance to safe stopping places, and an approval route.
60. **Would a pilot trust a minutes-left number?** We found no study on drivers. Related work says drivers over-trust displays that hide uncertainty, so we show "at least", a confidence flag, and every assumption. We do not claim pilots will trust it.

---

## Say these limits before a judge does

1. Every loco number is an assumption, except the leak rate (PLW test sheets).
2. Tests run on our simulation, not a real loco.
3. In the 144-run harness the advisor knows the true faults; Auto-diagnose gets the whole set right about two times in three.
4. "Stop at the nearest safe place" assumes a safe place about 3 km ahead.
5. The real-data work is a metro compressor proxy, and its detectors are weak.
6. Conventional 2-converter locos only; 3-phase load sharing is not modelled.
7. Decision support, not a certified safety system.

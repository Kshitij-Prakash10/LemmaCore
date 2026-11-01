# Slides: Failover Guardian (5 minutes, then 3 minutes of questions)

Numbers come from `demo_outputs/coverage.json` (core 0.1, seed 1) and `CONTEXT.md` section 4. Items marked **PENDING** depend on Agent B's app and models, which had not landed at 14:38. Updated 14:58: the app, the classifier and the sourced leak rate are now on main; see `demo-script.md`. Do not say them until the file named in the evidence line exists.

---

## Slide 1. The problem (0:00 to 0:45). Rubric: Problem selection, 20

**On screen:** "Converter fails mid-section. The backup does not take over. What now?" A one-line power diagram: SIV -> blowers, oil pump, brake compressor, charger, AC, lights.

**Say:** "A loco pilot is in the middle of a section. The auxiliary converter that runs the cooling blowers and the brake compressor trips. There is a standby, but sometimes it does not take over. Nobody tells the pilot what to switch off or how long they have before the motors overheat. That is our user and our problem."

**Evidence:** RDSO minutes, 29 May 2025: sheds report load not shifting from SIV1 to SIV2 (Siemens), and not shifting when the front-panel MCB trips (Medha).

---

## Slide 2. Evidence and root cause (0:45 to 1:30). Rubric: Understanding, 15

**On screen:** "582 failures, 2,116 units, FY 2024-25: about 27 per 100 units a year (conventional electric locos)". Below it: "Fault log keeps 20 days. Loco visits are 60 days apart."

**Say:** "RDSO expressed serious concern about these failures. Their table gives 582 failures across 2,116 units, about 27 per 100 a year by our arithmetic. These are conventional electric locos, not the 3-phase locos BLW builds. Two root causes stand out: the changeover to the standby is not reliable, and the fault log keeps 20 days while the loco comes in every 60, so the evidence is gone before anyone reads it."

**Evidence:** `CONTEXT.md` section 4, rows 1 to 4. The total and "per 100" are our reading of Annexure-I.

---

## Slide 3. What exists and the gap (1:30 to 2:00). Rubric: Understanding

**On screen:** two columns. "Exists: REMMLOT remote monitoring, loco thermal protection that derates or trips." "Missing: a crew-side answer to: what do I switch off, how long do I have, do I stop?"

**Say:** "Remote monitoring reports health to the shed. The loco's own protection derates or trips the motor. Neither tells the crew what to do next. We searched and found no crew advisor. We say 'we found none', not 'none exists'."

**Evidence:** `CONTEXT.md` section 4, rows 7 and 8 (trust: medium).

---

## Slide 4. Our idea (2:00 to 2:45). Rubric: Idea and innovation, 20

**On screen:** one diagram. Sensors -> [Diagnose: which faults?] -> [Advisor: shed, minutes left, decision] -> pilot. Beside it: [Fault-injection harness: 36 fault combinations x 4 conditions x 2 policies = 288 runs] -> coverage map.

**Say:** "Two parts. First, the advisor: one screen that says what to switch off, at least how many minutes are left, what runs out first, and whether to continue, stop at the next safe place, or stop now. Second, the proof: we inject every single and double fault in four conditions, with and without the advisor, and check four safety properties in every run. ML names the fault from noisy sensors, so the pilot does not have to know which unit failed. The advisor is physics first; ML supports it and may never make it more optimistic."

**Evidence:** `CONTRACT.md` sections 1 and 4; `docs/model.md` "Advisor".

---

## Slide 5. Live demo (2:45 to 3:45). Rubric: Prototype 10, Hard case 15

**On screen:** the app. Follow `docs/presentation/demo-script.md`.

**Say (headline):** "Across 144 cases, the baseline, which keeps running with only the loco's own protection, hits a limit while moving in 44. With the advisor, zero. All four safety properties held in every run. The price is 8 stops the baseline did not need, because we chose to be cautious."

**Say (hard case cell, hot climb, standby stuck):** "Without the advisor the motor reaches its trip limit about 12.6 minutes after the fault, while still moving. The advisor's cautious estimate is at least 6.3 minutes; the model's nominal value is 8.8. That is not enough for the station, so it says stop at the next safe place, and no limit is hit."

**Say (wrong data):** "Now we stick the temperature sensor. The reading goes flat while the model says the motor should be heating. The advisor flags the disagreement, lowers its confidence and assumes the motor is near the trip."

**Say (Auto-diagnose):** "The classifier names the fault from noisy sensors. On held-out simulated scenarios it gets the exact fault set right 55 percent of the time after a fault, and catches a stuck sensor every time. Below 60 percent confidence the advisor ignores it." Source: `models/metrics.json`.

**Evidence:** `demo_outputs/coverage.json` summary and case `STANDBY_STUCK__hot_climb`.

---

## Slide 6. What we left out and our assumptions (3:45 to 4:15). Rubric: Idea and innovation

**On screen:** "Left out: failure prediction, passenger features, cloud, safety-certification claims." "Every loco value tagged ASSUMED until a mentor confirms." "In the harness the advisor gets the true faults; in the app it gets the classifier's guess."

**Say:** "We kept the scope narrow on purpose. Every loco number in our config is tagged assumed, and the app shows the badge. Our 0 unsafe is a model result with assumed values, and with the advisor told the true fault. We also measured which assumptions matter: in the hard case, moving the motor trip temperature by 20 percent changes minutes-left from about 5 to about 13. That is the first value we need a railway engineer to confirm."

**Evidence:** `config/loco.json` (every block `"status": "assumed"`); `coverage.json` `advisor_policy_note`; `demo_outputs/sensitivity.json` (hot_climb_standby_stuck: trip temperature 4.91 to 13.31 min, swing 8.4; cool_flat_compressor_fail: brake-air minimum swing 48.0). Leak rate sourced from PLW dispatch test sheets (`docs/public_answers.md`).

---

## Slide 7. Future scope and disclosure (4:15 to 5:00). Rubric: Future scope, 10

**On screen:** four bullets plus the disclosure line.

**Say:** "Four steps to real use. One: replace our simulated faults with the converter makers' real fault codes. Two: offer the harness to RDSO as an acceptance test for converter changeover software. Three: model BLW's 3-phase locos, where three converters share the load and the frequency drops to about 37 Hz instead of loads going dark. Four: keep 60 days of fault log, not 20, so the shed sees the evidence. Who adopts it: RDSO for the test, the zonal sheds for the advisor. What it needs: maker fault codes, shed data and an approval route."

**Disclosure (say verbatim):** "We used Claude, an AI assistant, to research sources and help write code. The running tool contains no language model. We wrote our own tests and marked every assumed value."

**Evidence:** `docs/AI_DISCLOSURE.md`; converter count is a setting in `config/loco.json`.

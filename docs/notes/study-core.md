# Study sheet: the core (plant models, advisor, fault harness)

Code: `failover/core/`. Notes: `docs/model.md`. Results: `demo_outputs/coverage.json`, `demo_outputs/sensitivity.json` (core 0.1, seed 1).

## In one sentence
A small physics model of the converters, motor heat, brake air and battery. On top of it, an advisor picks which loads to keep, gives a cautious "at least N minutes" and decides continue or stop. A harness then injects every single and double fault to prove the advisor works.

## Five facts to know (and where they come from)
1. **Faults and runs.** 8 faults give 8 singles plus 28 pairs, so 36 combinations. Times 4 conditions (cool or hot, 30 or 45 C; flat or climbing at 2.7 percent, 1 in 37), that is 144 cases per policy and 288 runs, in about 1.2 to 1.3 s. Source: `CONTRACT.md` section 1, `coverage.json`.
2. **Result.** Baseline unsafe in 44 of 144, advisor unsafe in 0, 8 stops the baseline did not need, 0 failed properties. All 44 unsafe cases are on climbs and all are motor temperature. **In the harness the advisor is given the true faults.** Source: `coverage.json` summary.
3. **Heat model.** One thermal node: `C dT/dt = Q - h (T - T_amb)`. With the blower off, h falls to 15 percent. Q is zero when stopped. A closed form gives the time to the trip, and a test checks it against stepping within 1 percent. The loco's protection halves Q within 10 C of the trip (180 C, assumed). Source: `docs/model.md`.
4. **Advisor.** It tries all 128 subsets of the 7 loads and keeps those the healthy units can power. It prefers more essential loads, then more minutes, then more load kept. Minutes left is the 5th percentile over 200 random parameter draws. It continues if the station is within 0.8 of that figure; otherwise it stops at the next safe place (assumed 3 km) if that fits, else it stops now. Source: `docs/model.md`.
5. **Hard case** (hot climb, standby stuck). The baseline trips on motor temperature about 12.6 min after the fault, while moving. The advisor says at least 6.3 min (8.8 nominal), sheds nothing, and stops at the next safe place, so no limit is hit. Most sensitive assumption: the trip temperature (plus or minus 20 percent gives 4.9 to 13.3 min). Source: `coverage.json` `STANDBY_STUCK__hot_climb`, `sensitivity.json`.

## Three hard questions and answers (no reading from a screen)
1. **Q: Zero unsafe sounds too good.** A: It is our model with assumed parameters, and the advisor is told the true fault. In the app it gets the classifier's guess. Our ranges were tuned so the baseline fails at all; we logged every tuning step in `docs/model.md`.
2. **Q: How do you handle a wrong sensor?** A: If the motor temperature reading is exactly flat for 8 samples while the model says it should change by more than 0.05 C/s, the advisor flags `temp_sensors_disagree`, lowers its confidence and assumes the motor is 5 C below the trip. We tried a slope-based check first and dropped it because it fired by chance when the trend reversed.
3. **Q: Why does a hot day give no more failures than a cool one?** A: In our current model the gradient dominates: both climbing conditions give 22 unsafe cases and both flat conditions give 0. We have asked the core owner to check this (`docs/requests/20261101-1438-agentC-pitch-claims-check.md`). Until they reply: "In our model the climb drives the heat. We have flagged ambient as something to check."

## What I do not know, and how I will say so
- No parameter is confirmed. "Every value is tagged assumed. The two we most need confirmed are the motor trip temperature and the brake-air minimum."
- Known limits: a derated loco is not slowed; there is a single thermal node; the converter temperature is derived.
- 8 false stops: "We chose caution. A needless stop costs minutes; a motor trip mid-section costs much more."

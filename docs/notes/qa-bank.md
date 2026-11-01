# Q&A bank: 25 likely judge questions, short honest answers

Sources: `CONTEXT.md`, `CONTRACT.md`, `docs/model.md`, `config/loco.json`, `demo_outputs/coverage.json` (core 0.1, seed 1). Answer in your own words; these are the facts to hit. **[PENDING]** means it depends on Agent B's work, which was not merged at 14:38.

## Problem selection (20)

1. **Why this problem?** The BLW session asked "if this component fails during a journey, what should the system do next?" RDSO's own minutes show the auxiliary converter fails often and the standby sometimes does not take over. The user is specific: the loco pilot, mid-section.
2. **Is 27 per 100 a real figure?** It is our arithmetic from RDSO's FY 2024-25 table: 582 failures in 2,116 units. The table is primary; the total and its meaning are our reading. It is for conventional electric locos only.
3. **Doesn't the loco already protect itself?** Yes. It derates and trips the motor. That protects the motor but it does not tell the crew what to switch off or whether to stop. Our baseline includes that protection and is still unsafe in 44 of 144 cases.
4. **Who would use this day to day?** The loco pilot and assistant, on the cab screen. Secondarily, shed electricians and RDSO, who would use the harness as a test.

## Understanding of the problem (15)

5. **What is the root cause?** The changeover to the standby is not reliable (Siemens after a fault, Medha when the MCB trips), and the 20-day fault log is gone before the 60-day shed visit, so causes are never found. The makers did not share root-cause analyses.
6. **What exists today?** REMMLOT remote monitoring reports health to the shed. CLW specified analytics for 3-phase locos (April 2024; deployment status unknown). Neither is a crew advisor, as far as we found. Say "we found none".
7. **What does a failure cost?** Example: in October 2019 an auxiliary converter fault left three Vande Bharat coaches without AC, lights and fans for about an hour (news source, medium trust). We do not have a cost-per-failure figure and we will not invent one.
8. **What does the crew do today?** We found an older traction rule: try to resume within 20 minutes, else inform control (medium-low trust). We are asking the mentor to confirm current practice.

## Idea and innovation (20)

9. **What is new here?** Two things together: a crew-facing decision (shed, minutes left, continue or stop) and a fault-injection proof that checks it against every single and double fault. The proof is the test that earns trust; it is not a second product.
10. **Why physics and not just ML?** There is no real failure data for this loco to learn from. Physics gives limits we can explain. ML only diagnoses which fault is present, and a surrogate may lower the minutes left but never raise it.
11. **What did you leave out and why?** Failure prediction (no data), passenger features, cloud (the loco runs offline), and any safety-certification claim.
12. **Why the 5th percentile?** The pilot needs "at least N minutes", not an average. We draw 200 parameter sets within their ranges and report the 5th percentile, so the figure is cautious by design.

## Solution design and the hard case (15)

13. **What is the hard case?** A hot day on a 1-in-37 climb, unit 1 lost and the standby stuck. The baseline trips on motor temperature about 12.6 minutes after the fault, while moving. The advisor estimates at least 6.3 minutes (8.8 nominal), sees the station is too far, and stops at the next safe place. No limit is hit.
14. **Second hard case, wrong data?** The temperature sensor sticks. If the reading is exactly flat for 8 samples while the model says the motor should change by more than 0.05 C/s, the advisor flags `temp_sensors_disagree`, lowers its confidence and assumes the motor is 5 C below the trip.
15. **Does the advisor ever make things worse?** In our runs it never caused an unsafe case. It made 8 stops the baseline did not need: 6 with a dead sensor plus a heating motor, and 2 from the cautious 5th percentile. We think a needless stop is the right trade.
16. **What counts as unsafe?** A limit hit while the train is moving: motor temperature, brake air below the minimum, or battery empty. A controlled stop before any limit is not unsafe.
17. **Is 0 unsafe too good to be true?** It is a result from our model with assumed values, and in the harness the advisor is told the true faults. In the app it gets the classifier's guess. Real use needs validation with railway data.
18. **Why do only climbs fail?** In our model all 44 unsafe cases are climbs and all are motor temperature. Hot and cool days give the same count (22 each). We have asked Agent A why ambient makes no difference; until they reply, say "in our current model, gradient dominates". (Request: `docs/requests/20261101-1438-agentC-pitch-claims-check.md`.)

## Working prototype (10)

19. **Does it run offline?** Yes, by rule: no CDN, no cloud, no runtime downloads. One laptop, Wi-Fi off. **[PENDING: confirm on the presenting laptop at 15:30.]**
20. **How long does the proof take?** About 1.3 s for 288 runs. Every number regenerates with one command: `make harness`.
21. **How accurate is the classifier?** **[PENDING: read `models/metrics.json`. Quote held-out numbers only, and say it is trained on simulated data.]**

## Ownership and reasoning (10)

22. **Walk me through the heat model.** One thermal node for the motors: `C dT/dt = Q - h (T - T_amb)`. When the blower stops, h falls to 15 percent. Q depends on gradient and load and is zero when stopped. A closed form gives the time to the trip, and a test checks it against step-by-step simulation within 1 percent.
23. **How does the advisor choose what to shed?** It tries every subset of the 7 loads (128), keeps the ones the healthy converters can actually power, and prefers more essential loads, then more minutes, then more load kept. Note: in the hard case it sheds nothing; the stop decision is what saves it.

## Future scope and impact (10)

24. **Who adopts it, and what does it need?** RDSO for the harness as an acceptance test, and zonal sheds and crews for the advisor. It needs the makers' real fault codes, confirmed loco parameters, shed data and an approval route.
25. **Does it work for BLW's 3-phase locos?** The converter count is a setting (2 or 3; a vendor lists 3 x 130 kVA). The RDSO failure figures are not for 3-phase locos, and we say so.

## What we do not know (say it before they do)

- No loco parameter has been confirmed by a mentor; all are **assumed**. We know which ones matter most (`demo_outputs/sensitivity.json`): in the hard case the motor trip temperature (plus or minus 20 percent moves minutes-left from 4.9 to 13.3) and heat at full load (swing 5.1). For a failed compressor, the brake-air minimum (swing 16.0) and the leak rate (8.3).
- Real crew procedure today, and whether pilots would trust a minutes-left figure.
- The cost per failure.
- Whether REMMLOT or CLW's analytics are deployed, and what they show the crew.
- MetroPT-3 is a metro compressor in Porto, a proxy for brake air, not an Indian loco.

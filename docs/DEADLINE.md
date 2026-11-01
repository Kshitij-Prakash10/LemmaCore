# Deadline and how to compress the plan (humans fill in, agents obey)

**Build deadline: 15:30 IST, 1 November 2026. Presentations start at 16:00.** Hard stop at 15:30. Anything not merged to `main` by then does not exist.

The milestone tables in `AGENT_A.md` and `AGENT_B.md` assume about 105 minutes. We have far less. **Use these clock times instead of the minute counts in the briefs and in `CONTEXT.md`.** Run `date` at the start of each work chunk.

| Milestone | Clock target (IST) | What must be true |
|---|---|---|
| **M0** skeleton and contract | **14:40** | A: `types.py`, thin `simulate()` and `advise()` merged to `main`. B: environment checked, MetroPT-3 downloading or downloaded, stub core and app skeleton merged. |
| **M1** end-to-end hard case | **14:55** | One case runs from scenario to advice on screen with the real core: hot day, climbing, unit 1 trips, standby stuck. This is the progress-review slice. |
| **M2** proof and ML | **15:12** | `coverage.json` produced by the harness. Coverage map on screen. Classifier trained on core data and wired to "Auto-diagnose". |
| **M3** polish | **15:22** | Assumptions tab, what-if sliders, report export. Real-data tab only if it already works. |
| **Freeze** | **15:22 to 15:30** | No new features. Tests green on `main`. README steps work on a clean clone. App works with Wi-Fi off. `docs/STATUS_A.md` and `docs/STATUS_B.md` list AI and open-source use. |

If you fall behind a milestone, cut scope. Do not slip the clock.

## What to cut first

**Agent A:** keep the converter state machine, heat model, brake-air model, advisor, harness and `coverage.json`. Cut in this order: sensitivity output, battery model, Monte Carlo (use 100 runs, then a fixed parameter range), `report.html` polish.

**Agent B:** keep the app skeleton on the stub, the advisor tab, the coverage map and the fault classifier on core-generated data. Cut in this order: surrogate, Hindi labels, anomaly detector tuning, the MetroPT-3 leak fit. If the MetroPT-3 download fails or is slow, drop the real-data tab, write that in `docs/STATUS_B.md`, and keep everything else. Train the classifier before anything that depends on MetroPT-3.

**Never cut:** the advisor, the fault harness, the coverage map, the assumptions badges, offline operation.

## The progress review

A review will check that the solution runs and handles the hard case. Have the M1 slice working and merged before it, and keep `main` runnable at all times. A thin end-to-end slice beats a perfect module.

## After 15:30

15:30 to 16:00 is for the humans: rehearse the pitch with a timer, assign Q&A topics, and check the demo on the laptop that will present, with Wi-Fi off.

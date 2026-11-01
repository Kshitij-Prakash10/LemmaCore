# The big picture, in plain words

Sources: `CONTEXT.md`, `docs/model.md`, `docs/STATUS_A.md`, `demo_outputs/coverage.json` (core 0.1, seed 1, generated 09:06 UTC). Every loco value below is **assumed** until a mentor confirms it.

## The problem

An electric loco has a second power system next to the one that drives the wheels. The **auxiliary converter** (SIV, static inverter) feeds the cooling blowers, the oil pump, the brake-air compressor, the battery charger, the cab AC and the lights.

These converters fail often. RDSO's review of conventional electric locos (minutes of 29 May 2025) lists 582 failures across 2,116 units in FY 2024-25. **About 27 per 100 units a year is our own arithmetic** from that table. Most locos carry two converters so one can cover the other, but sheds told RDSO that the load sometimes **does not shift** to the healthy unit (Siemens 2x130 kVA after a fault, Medha 2x130 kVA when the front-panel MCB trips).

When that happens, the loco pilot is mid-section with no guide. Which loads should they switch off? How long before the traction motors overheat or the brake air drops? Should they carry on to the station or stop? Today there is no tool that answers this. Remote monitoring (REMMLOT) reports loco health to the shed; **we found no** crew-side advisor.

**Who it is for:** the loco pilot and assistant (a decision within minutes) and the shed electricians and RDSO engineers (who test converters).

## The solution: Failover Guardian

1. **The advisor.** One screen for the pilot. From the fault and the conditions it says: what to switch off, what to keep, **"at least N minutes"** left (a cautious 5th-percentile figure), what will run out first (heat, air, battery, power), and one decision: **continue**, **stop at the next safe place**, or **stop now**.
2. **The proof.** A fault-injection harness tries every single and double fault (8 faults give 36 combinations) in 4 conditions (cool or hot, flat or climbing), first with no advisor (baseline) and then with the advisor. That is 288 runs, and it takes about 1.3 s.
3. **ML support.** A classifier names the faults from noisy sensor readings, so the pilot does not need to know which unit failed. Real compressor data from a metro train (MetroPT-3, Porto) calibrates the brake-air leak model. It is a proxy, not an Indian loco.

## What the proof shows today (our model, assumed parameters)

- Baseline (keep running, the loco's own protection only): **unsafe in 44 of 144** cases.
- With the advisor: **unsafe in 0 of 144**, and all four safety properties held in every run.
- Cost of caution: **8 stops the baseline did not need** (6 with a dead temperature sensor, 2 from the cautious 5th percentile).
- **Caveat to say out loud:** in the harness the advisor is told the true faults. In the app it gets the classifier's guess instead, so the 0 is a best case.

## Why it matters

A converter fault mid-section becomes a stalled train, a motor trip or a brake-air problem. A clear "switch these off, you have at least N minutes, stop at the next safe place" turns guesswork into one decision. And the harness gives RDSO and the sheds a repeatable **acceptance test** for converter changeover logic, which they lack today.

## What we left out, on purpose

Failure prediction, passenger features, cloud, and any safety-certification claim. The tool runs fully offline on one laptop.

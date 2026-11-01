# Status: Agent A (core)

## Current milestone
M0, M1 and M2 done at 14:38. Starting M3 (sensitivity, notes) next.

## What works (14:38)
- **Harness (M2):** `python -m failover.core.harness --out outputs` (or `make harness`) runs 36 fault combinations x 4 conditions x 2 policies in about 1.3 s and writes `outputs/coverage.json`, `runs.csv` and `report.html`. A committed copy is in `demo_outputs/`. Result: baseline unsafe 44 of 144, advisor unsafe 0, 8 unneeded stops, 0 failed properties.
- Four properties checked per run (brake air, essential loads kept, no more load than power, minutes left never optimistic).
- `failover/core/types.py`, `version.py` (`CORE_VERSION` 0.1, `CONTRACT_VERSION` 0.2), `config.py`, `model.py`.
- `simulate(scenario, policy, config)` with the real converter, heat, brake-air and battery models. Deterministic given the seed.
- `advise(observation, config, fault_hypothesis)` with subset search, 5th percentile Monte Carlo, wrong-data flag and the continue or stop decision.
- `python -m failover.core.cli demo` shows the hard case: hot climb, standby stuck, station 15 km away. Baseline hits the motor temperature limit. Advisor stops at the nearest safe place.
- `tests/core/test_contract.py`: 16 tests (shapes, determinism, every fault runs, stuck sensor, advice shape, hard case, closed form against stepping).

## What is stubbed or incomplete
- Sensitivity output, battery refinements: not started.
- Fault inference from signals in `infer_faults` is rough. Use the classifier from Agent B.

## What I need from Agent B or a human
- Agent B: import `failover.core` from `main` and drop the stub. See `CONTRACT.md` 0.2 for the changes.
- Human: ask the mentor the five questions and give me the answers so I can flip config statuses.

## Tuning and assumption changes
- `thermal.motor.h_off_ratio` now min 0.10, nominal 0.15, max 0.25. `heat_full_kw` now min 70, nominal 90, max 110. Reason: with the first guesses the loco protection derate always saved the baseline, so no case was unsafe.

## AI and open-source use (required for disclosure)
- Claude Code (Agent A) wrote and reviewed code in failover/core, the tests and the docs in this area.
- Packages: numpy, scipy, pytest.

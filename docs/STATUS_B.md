# Status: Agent B (data, ML, app)

Update after every milestone. Keep it short and honest.

## Current milestone
Branch agent-b/ml-v2 (not merged to main): air-leak model v2, advisor hook, /evidence page. See docs/ml.md.
Optional leak flag added 15:13 (held-out recall 0, stays silent; hook tested). M2 done (14:53 IST). The app runs on the real core. The coverage map reads demo_outputs/coverage.json. The fault classifier is trained on core data and wired to Auto-diagnose. MetroPT-3 leak fit and anomaly detector done (14:56). M3 checked (14:56): live server returns 200 on every endpoint; report export falls back to demo_outputs/report.html; stuck-sensor hard case gives temp_sensors_disagree and STOP_NOW. Remaining: what-if speed slider not added (ambient, gradient, load, units, distance are there); surrogate (stretch) not built; Hindi labels not built.

## Environment check
Python 3.15.0 (not 3.14 as the brief says). In `.venv`: numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, Flask 3.1.3, scipy, joblib, pytest. All import. `ucimlrepo` installed but not used (curl download worked).

## What works
- MetroPT-3 downloaded to `data/raw/` and logged in `data/README.md` (size, sha256, row count). The file has 1,516,948 rows at 10 s spacing. The PDF says 15,169,480 at 1 Hz. Noted.
- `data/processed/failures.json`: the four air-leak events from the bundled PDF.
- `failover/stubs/stub_core.py`: shape-correct fake core per CONTRACT.md 0.1 (Scenario, SimResult, Advice, simulate, advise, a stub coverage.json).
- App (`python -m failover.app.server`, http://127.0.0.1:5000): tabs Advisor, Coverage map, Real data, Assumptions, Report. All endpoints from AGENT_B.md, plus `/api/status` and `/api/metrics`. No external assets.
- `failover/app/backend.py` uses `failover.core` automatically when `failover.core.types`, `.simulate` and `.advisor` import, and falls back to the stub otherwise. The UI shows a "STUB core" badge while on the stub.
- `tests/app`: 12 tests pass, with the network blocked.

- Fault classifier (`failover/ml/`): per-fault gradient boosting on 60 s observed windows from `failover.core.simulate`. Evaluation per the protocol is in `docs/ml.md` and `models/metrics.json`. `make train` reproduces it in about 40 s.
- Auto-diagnose feeds the advisor only when confidence is at least 0.6 and a fault is named. Otherwise the advisor infers from signals.
- `tests/ml`: no seed leakage, core version match, diagnose shape and speed (under 20 ms). 38 tests pass on the whole suite.

## What is stubbed or incomplete
- The stub core is kept only as a fallback. The app uses `failover.core`.
- MetroPT-3 leak fit (`air_params_fit.json`) and Isolation Forest anomaly detector are built, and shown on the Real data tab. With the threshold fixed in advance it caught 0 of 4 leaks. Lower budgets, all fixed in advance, catch up to 3 of 4. See docs/ml.md.
- The minutes-left surrogate (stretch) is not built. `infer.minutes_left_p5` returns None.

## What I need from Agent A or a human
- Agent A: for information, STANDBY_STUCK, MCB_TRIP and U1_TRIP+STANDBY_STUCK give the same observed signals, so the classifier cannot separate them. That is fine if the advisor treats them alike. No action needed.
- Human: rerun `make train` if CORE_VERSION changes (a test fails when it does).

## Metrics (copy from models/metrics.json, held-out only)
See `docs/ml.md`. Held-out seeds, post-fault windows: exact fault-set accuracy 0.55. TEMP_SENSOR_STUCK precision 1.0, recall 0.99. Unseen pairs: 2 of 4 fully found.

## AI and open-source use (required for disclosure)
- Claude Code (Agent B, model Claude Opus 5.5) wrote and reviewed code in failover/ml, failover/app, failover/stubs, tests/app, tests/ml and data/README.md.
- Dataset: MetroPT-3, UCI Machine Learning Repository, CC BY 4.0. Citation: Davari, N., Veloso, B., Ribeiro, R., and Gama, J. (2021).
- Packages: pandas, scikit-learn (HistGradientBoostingClassifier), joblib, flask (and numpy, scipy, pytest from the core requirements).

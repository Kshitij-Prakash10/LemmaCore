# Status: Agent B (data, ML, app)

Update after every milestone. Keep it short and honest.

## Current milestone
M0 done (14:31 IST). Starting M1: switch to the real core when it lands, MetroPT-3 loader, leak fit, anomaly baseline.

## Environment check
Python 3.15.0 (not 3.14 as the brief says). In `.venv`: numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, Flask 3.1.3, scipy, joblib, pytest. All import. `ucimlrepo` installed but not used (curl download worked).

## What works
- MetroPT-3 downloaded to `data/raw/` and logged in `data/README.md` (size, sha256, row count). The file has 1,516,948 rows at 10 s spacing. The PDF says 15,169,480 at 1 Hz. Noted.
- `data/processed/failures.json`: the four air-leak events from the bundled PDF.
- `failover/stubs/stub_core.py`: shape-correct fake core per CONTRACT.md 0.1 (Scenario, SimResult, Advice, simulate, advise, a stub coverage.json).
- App (`python -m failover.app.server`, http://127.0.0.1:5000): tabs Advisor, Coverage map, Real data, Assumptions, Report. All endpoints from AGENT_B.md, plus `/api/status` and `/api/metrics`. No external assets.
- `failover/app/backend.py` uses `failover.core` automatically when `failover.core.types`, `.simulate` and `.advisor` import, and falls back to the stub otherwise. The UI shows a "STUB core" badge while on the stub.
- `tests/app`: 12 tests pass, with the network blocked.

## What is stubbed or incomplete
- All advice and coverage numbers are fake (STUB) until Agent A's core lands.
- Classifier, anomaly detector and leak fit are not built yet. Auto-diagnose says "classifier not built yet".

## What I need from Agent A or a human
- Agent A: `failover/core/types.py` with `Scenario` accepting every CONTRACT field as a keyword (the app passes all of them), plus `simulate.simulate` and `advisor.advise`. Please export `CORE_VERSION` from `failover/core/__init__.py`.
- Please commit `demo_outputs/coverage.json` as soon as the harness runs once.

## Metrics (copy from models/metrics.json, held-out only)
(none yet)

## AI and open-source use (required for disclosure)
- Claude Code (Agent B, model Claude Opus 5.5) wrote and reviewed code in failover/ml, failover/app, failover/stubs, tests/app, tests/ml and data/README.md.
- Dataset: MetroPT-3, UCI Machine Learning Repository, CC BY 4.0. Citation: Davari, N., Veloso, B., Ribeiro, R., and Gama, J. (2021).
- Packages: pandas, scikit-learn, joblib, flask (and numpy, scipy, pytest from the core requirements).

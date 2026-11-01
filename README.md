# Failover Guardian

Node Quest 2026 entry (team LemmaCore). When a loco's auxiliary converter fails and the backup does not take over, the loco pilot gets one decision: what to switch off and how many minutes are left. A fault-injection test proves the advisor handles every single and double converter fault. Machine learning diagnoses the fault from sensor windows and is calibrated and demonstrated on real compressor data.

Everything runs offline on one laptop.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
make test       # all tests
make harness    # fault-injection test, writes outputs/coverage.json, outputs/report.html
make train      # trains the ML models (needs data/raw from setup)
make app        # starts the app at http://127.0.0.1:5000
make demo       # harness, train, then app
```

## Layout

| Path | What |
|---|---|
| `failover/core` | plant models, advisor, fault harness (Agent A) |
| `failover/ml` | data loading, training, inference (Agent B) |
| `failover/app` | offline web app (Agent B) |
| `config/loco.json` | every loco parameter, tagged assumed or confirmed |
| `CONTEXT.md` | competition rules, problem, solution, scope |
| `CONTRACT.md` | interfaces between the two agents |
| `OWNERSHIP.md` | who owns which files, git rules |
| `docs/` | status files, model notes, requests, AI disclosure |

## Honesty notes

All loco parameters are team assumptions until a mentor confirms them. The classifier is trained on simulated data. The real-data component uses a metro train compressor dataset as a proxy. See `docs/model.md` and `docs/ml.md` once they are written.

## Train and run

```bash
make train   # trains every ML model; needs data/raw/metropt3.csv for the real-data parts
make app     # http://127.0.0.1:5000 (works offline; model evidence is at /evidence)
```

The app runs with no model files. It falls back from the v2 leak model to the v1 flag, then to no ML, and the advice is then the same as with no ML.

## Data sources and licences

- **MetroPT-3:** UCI Machine Learning Repository, dataset 791, CC BY 4.0. Metro train compressor in Porto. Downloaded during setup and not committed. Details: `data/README.md`.
- **MetroPT-2 (optional, external test only):** Zenodo 7766691, CC BY 4.0. Not included and not yet run. Place it at `data/MetroPT2.csv`.

## Disclosure

Code was written with Claude Code (AI agents, Claude Opus 5.5) and reviewed by the team. Open-source packages: numpy, scipy, pandas, scikit-learn, joblib, Flask, pytest.

ML in the app: a fault classifier trained on our simulator, and an optional air-leak flag on real metro compressor data used as a proxy. The leak flag's IsolationForest alerted at some point in 4 of 4 held-out events at 0.36 false alarms per day, but the threshold was chosen on those same folds and the alert is on for only 2 to 26 % of each event. The supervised alternative caught 1 of 4. The flag can only shorten the advisor's air clock, never lengthen it. See `docs/ml.md`.

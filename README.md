# Failover Guardian

**Node Quest 2026: won 2nd place** (IEEE IES Student Branch, IIT BHU, 1 Nov 2026; final round of the top 8). Results below are from simulation with assumed loco values, not a real loco; the real-data part uses a metro compressor dataset as a proxy.

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
make train      # retrains the ML models; the real-data parts need data/raw/metropt3.csv (see data/README.md)
make app        # development server at http://127.0.0.1:5000 (model evidence at /evidence)
make demo       # harness, train, then app
```

The trained models are committed in `models/`, so `make train` is optional. The app also runs with no model files: it falls back from the v2 leak model to the v1 flag, then to no ML, and the advice is then the same as with no ML.

## Deploy

The app is a Flask WSGI app at `failover.app.server:app`. It needs no network at run time.

```bash
pip install -r requirements-deploy.txt
gunicorn --workers 2 --timeout 120 --bind 0.0.0.0:8000 failover.app.server:app
```

Or with Docker:

```bash
docker build -t failover-guardian .
docker run --rm -p 8000:8000 failover-guardian
```

Or on Vercel: import the repository with the framework preset **Other** and no build or output settings. `api/index.py` is the entry point and `vercel.json` routes every path to it. The function bundle is large (numpy, scipy, pandas, scikit-learn, about 340 MB installed); if Vercel rejects it for size, use the Docker image on a container host instead.

`make serve` runs gunicorn locally (`HOST` and `PORT` override the bind address). `/api/status` is a cheap health check. Bad API input answers HTTP 400 with `{"error": "..."}`.

Package versions are pinned in the requirements files. The committed `models/*.joblib` files are scikit-learn pickles: keep scikit-learn and joblib at the pinned versions, or run `make train` after upgrading. Retraining the fault classifier with other library versions can move its metrics in the third decimal place.

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
| `Dockerfile`, `requirements-deploy.txt` | production image and WSGI server |
| `api/index.py`, `vercel.json` | Vercel entry point and routing |

## Honesty notes

All loco parameters are team assumptions until a mentor confirms them. The classifier is trained on simulated data. The real-data component uses a metro train compressor dataset as a proxy. See `docs/model.md` and `docs/ml.md`.

## Data sources and licences

- **MetroPT-3:** UCI Machine Learning Repository, dataset 791, CC BY 4.0. Metro train compressor in Porto. Downloaded during setup and not committed. Details: `data/README.md`.
- **MetroPT-2 (optional, external test only):** Zenodo 7766691, CC BY 4.0. Not included and not yet run. Place it at `data/MetroPT2.csv`.

## Disclosure

Code was written with Claude Code by two agents working in parallel (Agent A, the core, harness and app interface: Claude Sonnet 5.5; Agent B, the ML and app backend: Claude Opus 5.5) and reviewed by the team. A third Claude helped with the presentation notes and slides. Open-source packages: numpy, scipy, pandas, scikit-learn, joblib, Flask, pytest, gunicorn (deployment only).

ML in the app: a fault classifier trained on our simulator, and an optional air-leak flag on real metro compressor data used as a proxy. The leak flag's IsolationForest alerted at some point in 4 of 4 held-out events at 0.36 false alarms per day, but the threshold was chosen on those same folds and the alert is on for only 2 to 26 % of each event. The supervised alternative caught 1 of 4. The flag can only shorten the advisor's air clock, never lengthen it. See `docs/ml.md`.

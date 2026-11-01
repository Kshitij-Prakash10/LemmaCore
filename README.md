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

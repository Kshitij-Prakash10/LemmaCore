# Agent B brief: data, machine learning and the app

You own `failover/ml/**`, `failover/app/**`, `failover/stubs/**`, `data/**`, `models/**`, `tests/ml/**`, `tests/app/**`, `docs/ml.md` and `docs/STATUS_B.md`. Read `CONTEXT.md`, `OWNERSHIP.md` and `CONTRACT.md` first. Your branch is `agent-b/ml-app`.

Your job in one line: turn the core's simulations and one real dataset into trustworthy ML components, and present everything in an offline app the judges can click through. Agent A builds the physics and the advisor. Until the real core lands at checkpoint I1, you work against `failover/stubs/stub_core.py`, which you write to match `CONTRACT.md` (shape-correct, obviously fake numbers, clearly labelled).

## What you build

### 1. Real data: MetroPT-3 (`failover/ml/data_metropt.py`)
- The public dataset is MetroPT-3 (UCI Machine Learning Repository, dataset id 791, CC BY 4.0), real sensor data from the air production unit (compressor) of a metro train in Porto: pressures, motor current, oil temperature, valve signals, with maintenance-confirmed air-leak failures. It is a **proxy** for a loco's brake-air system and we say so everywhere.
- **Download it now, while there is internet**, to `data/raw/` (not committed). The `ucimlrepo` package or the UCI page both work. Record the file size, row count and sha256 in `data/README.md`. Sources disagree on row count and on the recording period, so verify from the file itself and write down what you find.
- Parse the failure table (start and end times of the air-leak events) from the UCI page. Store it in `data/processed/failures.json` with the source noted.
- Use chunked reading. The file can be large.

### 2. Brake-air parameter fit (`fit_air_params.py`)
- From segments where the compressor is off, estimate the pressure decay rate in bar per minute with a confidence interval (bootstrap).
- Write `data/processed/air_params_fit.json`: `{"leak_bar_per_min": {"min": ..., "nominal": ..., "max": ...}, "n_segments": ..., "source": "MetroPT-3 proxy", "status": "fitted_proxy"}`. Agent A reads it only if the config says so.
- Document the limits: metro train, not a loco; compressor behaviour differs.

### 3. Real-data anomaly detector (`train_anomaly.py`)
- Train on the first month of normal data (the dataset notes suggest this split). Test on later data containing the labelled failure windows.
- Start with Isolation Forest on windowed features (rolling means, standard deviations, slopes). Add an autoencoder only if time remains.
- Report precision, recall and false alarms per day at a fixed false-alarm budget, plus the lead time before each labelled failure. Save `models/anomaly.joblib`, `models/anomaly_metrics.json` and `data/processed/anomaly_demo.json` (a replay the app can animate).
- Honest framing: this shows we handle real sensor data, not that the metro result transfers to a loco.

### 4. Scenario dataset (`make_dataset.py`)
- Generate training scenarios by calling `failover.core.simulate.simulate`, **never your own physics**. Vary ambient 20 to 48 C, gradient 0 to 3 percent, loaded or empty, 2 or 3 units, distance to the next station, speed, sensor noise 0 to 0.1, and parameter overrides of plus or minus 20 percent (domain randomization). Include healthy runs, all 8 single faults and pairs.
- Record `core_version`, seed and generation date in the dataset metadata. Save to `data/processed/scenarios.csv` (or parquet). Use multiple processes. Aim for at least 5,000 labelled windows, more if cheap.
- Label: the set of active faults (multi-label). Features: statistics over a 60 s window of **observed** signals only (mean, standard deviation, slope, min, max, last value, plus differences between related signals).

### 5. Fault diagnosis classifier (`train_fault_clf.py`, `infer.py`)
- A multi-label model (start with gradient boosting or random forest, one output per fault) that returns a probability per fault.
- **Evaluation protocol (this is what the judges will probe):**
  - Split by scenario seed, never by row.
  - Hold out whole fault pairs the model never saw in training and report recall on them.
  - Report results at noise 0, 0.05 and 0.1.
  - Report results on scenarios with parameters outside the training range by plus or minus 30 percent.
  - Report per-fault precision and recall, a confusion view for `TEMP_SENSOR_STUCK`, and calibration (reliability curve).
- Save `models/fault_clf.joblib` and `models/metrics.json` (with the core version). Inference under 20 ms. If confidence is below 0.6, `diagnose()` returns `confidence` low, and the app tells the advisor to use the cautious assumption.
- Honest framing: it is trained on simulated data and is only as good as the simulator. Say what the held-out tests show and what they cannot.

### 6. Minutes-left surrogate (stretch, `train_surrogate.py`)
- Quantile gradient boosting for the 5th percentile of minutes left, trained on core outputs. Compare with the physics value on held-out scenarios. Enforce the safety rule in `CONTRACT.md`: it may only lower the advisor's value.

### 7. The app (`failover/app/`)
Flask server plus static HTML, CSS and JavaScript. **No CDN, no web fonts from the internet, no external libraries.** Draw charts with plain canvas or SVG. It must work with Wi-Fi off.

Endpoints:
- `GET /api/config` returns the loco config with each value's `status` badge.
- `POST /api/advise` takes a scenario or an observation and returns the advice (and, if asked, the diagnosis first).
- `POST /api/diagnose` takes an observed window and returns the classifier output.
- `GET /api/coverage` returns `outputs/coverage.json`, or `demo_outputs/coverage.json` if the first is missing.
- `GET /api/anomaly-demo` returns the replay from step 3.
- `GET /api/report` serves the report from the harness.

Screens (tabs):
1. **Advisor.** The one-decision card: switch off, keep on, minutes left (p5) with the limiting factor, continue or stop, flags. Beside it a chart of temperature and air pressure for baseline and advisor. What-if sliders for ambient, gradient, train load. Buttons: "Inject fault" (pick faults), "Auto-diagnose", "Stick the temperature sensor".
2. **Coverage map.** The 36 fault combinations by 4 conditions, coloured safe, controlled stop or unsafe, for baseline and advisor side by side. Clicking a cell opens that case in the Advisor tab. Headline numbers from the file.
3. **Real data.** The MetroPT-3 replay and metrics, with the proxy warning.
4. **Assumptions.** Every config value with its `assumed` or `confirmed` badge and source.
5. **Report.** Export button for the test report.

Design: large type, three lines for the decision, plain words. Hindi and English labels are a stretch.

## Milestones (from the start of the build)

| By | Deliver | Done when |
|---|---|---|
| **M0, 10 min** | Environment check (Python 3.14, install `requirements-ml.txt`, confirm scikit-learn and Flask import, tell the human if not). MetroPT-3 downloaded and logged in `data/README.md`. `stubs/stub_core.py`. App skeleton showing the stub's advice. | The app runs offline on the stub. |
| **M1, 35 min** | Switch to the real core at checkpoint I1. Advisor tab live. MetroPT-3 loader and exploration, the failure table, the leak-rate fit. Anomaly detector baseline with metrics. | The hard case shows on screen from the real core. |
| **M2, 70 min** | Dataset generation, classifier trained and evaluated per the protocol, `infer.diagnose`, "Auto-diagnose" wired in. Coverage map reading `coverage.json`. | The coverage map and the classifier both work on real core output. |
| **M3, 95 min** | Assumptions tab, report export, what-if sliders, real-data tab, surrogate if time allows. `docs/ml.md` with metrics and honest limits. | Every tab works with Wi-Fi off. |
| **Freeze, last 15 min** | Tests green, README run steps verified on a clean clone, models committed (keep them small), `docs/STATUS_B.md` lists AI and open-source use. | |

## Tests you write
Dataset has no seed leakage between train and test; model file records the current core version; `diagnose` returns probabilities that sum sensibly and runs under 20 ms; anomaly detector runs on a saved sample; every endpoint returns valid JSON; the app starts with no network (set a socket guard in the test).

## Do not
- Edit `failover/core`, `config` or `CONTRACT.md` or any human-owned file. Write a request file instead.
- Re-implement the physics. Always call the core.
- Report a metric that was not computed on held-out data. Never tune on the test split.
- Load anything from the internet at run time.
- Commit `data/raw`. Keep committed models small (a few MB at most).

## First 10 minutes
1. `git pull`, create `agent-b/ml-app`, read the four documents.
2. Create a virtual environment, install `requirements-ml.txt`, and run the environment check. Report problems immediately in `docs/STATUS_B.md`.
3. Download MetroPT-3 and start `data/README.md`.
4. Write the stub core and the app skeleton. Merge to `main`.

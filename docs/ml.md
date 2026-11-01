# ML notes (owner: Agent B)

All numbers below are copied from `models/metrics.json` (core version 0.1, seed 7). They come from held-out data only. Reproduce with `make train` (`python -m failover.ml.train_all`).

## Fault diagnosis classifier

- **Data (synthetic).** Windows of 60 s of **observed** signals, cut from `failover.core.simulate` runs (baseline policy) at 60, 120, 300 and 600 s. The fault is injected at 60 s, so the first window is healthy. 37 fault sets (healthy, 8 singles, 28 pairs) x 40 random scenarios: ambient 20 to 48 C, gradient 0 to 3 %, loaded or empty, 2 or 3 units, distance, speed, noise 0 to 0.1, and +-20 % on five physics parameters (domain randomization). No physics in our code.
- **Model.** HistGradientBoostingClassifier, one per fault (binary relevance), 100 iterations. Features: mean, standard deviation, slope, min, max and last value of each observed signal, plus the power margin, the unit load difference and a flat-temperature check.
- **Split.** by scenario seed (20% of seeds held out); 4 fault pairs never seen in training. Training: 4224 windows from 1056 scenarios.
- **Inference.** About 14 ms per window on this laptop (test limit 20 ms).

### Held-out seeds, post-fault windows (threshold 0.5)

Exact fault-set accuracy 0.551, micro precision 0.807, micro recall 0.731.

| Fault | Precision | Recall | Support |
|---|---|---|---|
| U1_TRIP | 0.896 | 0.691 | 162 |
| U2_TRIP | 1.0 | 1.0 | 171 |
| STANDBY_STUCK | 0.546 | 0.589 | 192 |
| MCB_TRIP | 0.415 | 0.477 | 153 |
| UNIT_DERATE | 0.958 | 0.892 | 204 |
| BLOWER_FAIL | 0.941 | 0.607 | 183 |
| COMPRESSOR_FAIL | 0.891 | 0.582 | 141 |
| TEMP_SENSOR_STUCK | 1.0 | 1.0 | 141 |

TEMP_SENSOR_STUCK confusion (all test windows): TP 141, FP 0, FN 0, TN 915.

### Fault pairs never seen in training

| Pair | Both found | Per-fault recall |
|---|---|---|
| U2_TRIP+BLOWER_FAIL | 1.0 | U2_TRIP 1.0, BLOWER_FAIL 1.0 |
| MCB_TRIP+COMPRESSOR_FAIL | 0.05 | MCB_TRIP 0.442, COMPRESSOR_FAIL 0.275 |
| UNIT_DERATE+TEMP_SENSOR_STUCK | 1.0 | UNIT_DERATE 1.0, TEMP_SENSOR_STUCK 1.0 |
| U1_TRIP+COMPRESSOR_FAIL | 0.0 | U1_TRIP 1.0, COMPRESSOR_FAIL 0.0 |

### Robustness

- Exact-set accuracy by noise level: 0.0: 0.713, 0.05: 0.66, 0.1: 0.63.
- Parameters outside the training range (scaled 0.7 to 0.8 or 1.2 to 1.3): exact-set accuracy 0.691.
- Reliability curve: `reliability_test` in `models/metrics.json`.

### What this does and does not show

- STANDBY_STUCK, MCB_TRIP and U1_TRIP plus STANDBY_STUCK all mean "unit 1 lost and its loads not moved" in the simulator, so their observed signals are the same. No classifier can tell them apart from these signals. Their low precision and recall come from that, not from the model. The useful output is "unit 1 lost, no takeover", which the advisor handles the same way.
- COMPRESSOR_FAIL is often missed in the first minute after the fault, because the air pressure has barely moved yet.
- A first try with one joint random forest found 0 of 4 unseen pairs. One gradient-boosting model per fault found 2 of 4, so we use that.
- **Safety rule in the app.** The advisor gets the classifier's fault list only when confidence is at least 0.6 and at least one fault is named. Otherwise the advisor infers the faults from the signals (the cautious path), and the screen says so.
- Trained and tested on our simulator only. These numbers say how well the model inverts our simulator, not how it would do on a real loco.

## MetroPT-3 (real data, proxy)

Source and file checks are in `data/README.md`. A metro train compressor in Porto is **not** an Indian loco. These results show that we handle real sensor data. They do not show that the numbers transfer.

### Brake-air decay fit (`failover/ml/fit_air_params.py`)

- 9522 compressor-off segments (motor current under 1 A, at least 3 min), at least a day away from labelled failures.
- Reservoir pressure decay: median 0.0914 bar/min, 10th to 90th percentile 0.056 to 0.1442. Bootstrap 95 % interval of the median: 0.0908 to 0.0921.
- Written to `data/processed/air_params_fit.json` with status `fitted_proxy`. The core uses it only if `air.use_fitted` is true in the config (Agent A's choice). It is false now.
- Limit: off-segment decay includes normal air use (brakes, doors), so it overstates pure leakage. Its median is above the loco dispatch limit in the config (0.067 bar/min), which fits that reading.

### Anomaly detector (`failover/ml/train_anomaly.py`)

- IsolationForest(200 trees, seed 13) on 5min bin features, 6-bin trailing median. Trained on February 2020. Alarm threshold set on March 2020. Tested from 2020-04-01 (153.2 days, all four labelled air leaks).
- **Headline, threshold fixed in advance (0.999 quantile of the smoothed March score): 0 of 4 leaks caught, 0.0 false alarms per day.** The threshold was too strict.
- The score does separate the classes: median 0.6893 inside leak windows vs 0.4899 in normal running (99th percentile of normal: 0.6905).
- The other budgets, all fixed before testing and all reported. None was picked on the test months:

| March quantile | Threshold | Leaks caught | False alarms per day | Alarm precision |
|---|---|---|---|---|
| 0.95 | 0.6818 | 3 of 4 | 0.17 | 0.593 |
| 0.99 | 0.6967 | 1 of 4 | 0.104 | 0.038 |
| 0.995 | 0.6979 | 1 of 4 | 0.078 | 0.054 |
| 0.999 | 0.7102 | 0 of 4 | 0.0 | None |

- An early warning counts if the alarm comes up to 24 h before the leak starts. Per-event lead times are in `models/anomaly_metrics.json`.
- Honest reading: the detector finds the leaks as unusual, but the false-alarm trade-off depends on a threshold we could only set on one month of normal data.

### Optional supervised air-leak flag (`failover/ml/train_leak.py`, `leak_detector.py`)

- RandomForestClassifier(100 trees, max_depth 8, balanced classes, seed 42) on 1 min means with rolling 10 min features. Time-based split: trained on leaks 1 to 3 (before 2020-07-01), tested on leak 4 (from 2020-07-01, 62 days).
- **Result on held-out leak 4 at p > 0.5: recall 0.0, no alerts and no false alarms.** The highest probability inside leak 4 was 0.17, below the highest just outside it (0.21). The model learned nothing that carries over to this leak. Metrics: `models/leak_metrics.json`. Plot: `models/leak_test_period.svg`.
- App hook (`failover/app/backend.py`, the only change to the advice path): if p > 0.5, the advisor gets a copy of the config with the air leak rate times `LEAK_MULTIPLIER` = 2.0 (status assumed, shown on the Assumptions tab), and the card shows "Air leak suspected". With no model file or any error, p is None and the advice is identical (tested). The harness does not use the hook. Its 144-run summary is unchanged (44 baseline unsafe, 0 advisor unsafe, 0 property failures).


## Air-leak model v2 (`leak_features.py`, `train_leak_v2.py`, `leak_rate.py`, `external_test.py`)

Fallback chain: v2 model, then the v1 flag, then no ML. Each step is tested. Metrics: `models/leak_v2_metrics.json`, `models/leak_v2_cv_table.csv`. Page: `/evidence` in the app.

- **Features.** 1 min means. Over 60 min: cycles per hour, mean loaded-run and off durations, reservoir decay on unloaded minutes, recharge on loaded minutes, load duty. Over 10 min: mean and std of 7 signals. A row is loaded when motor current is above 4.75 A, the valley between the unloaded mode (3.5 to 4 A) and the loaded mode (5 to 6.5 A) in the histogram (`python -m failover.ml.leak_features`). The rate features use the mean minute-to-minute slope on those minutes, not a separate fit per period.
- **Physical signature.** During all four leaks the compressor stays loaded about 99 % of the time. It never unloads, so there is no off period to measure a decay on.
- **INVALID data.** A window is invalid if more than 20 % of its 60 minutes are missing or Reservoirs is flat for 10 min. Invalid minutes are never alarmed. No off period is not invalid. An earlier version wrongly treated it that way, and that hid almost every leak minute.
- **Evaluation.** Leave-one-event-out over E1 to E4. Test block: event +- 3 days. Training excludes a further 1 day guard. Alarm: p > theta in at least 7 of the last 10 minutes. An alert up to 2 h before the start counts as a detection.

| Model | Theta | Held-out event | Detected | Minutes to first alert | Share of event in alert | False alarms per day |
|---|---|---|---|---|---|---|
| RandomForest | 0.7 | E1 | no | - | 0 % | 0.0 |
| RandomForest | 0.7 | E2 | yes | 25.0 | 93 % | 0.0 |
| RandomForest | 0.7 | E3 | no | - | 0 % | 0.0 |
| RandomForest | 0.7 | E4 | no | - | 0 % | 0.0 |
| IsolationForest | 0.999 | E1 | yes | 364.0 | 2 % | 0.257 |
| IsolationForest | 0.999 | E2 | yes | 29.0 | 6 % | 0.468 |
| IsolationForest | 0.999 | E3 | yes | 30.0 | 26 % | 0.726 |
| IsolationForest | 0.999 | E4 | yes | 10.0 | 21 % | 0.0 |

- **Chosen: IsolationForest, theta 0.999.** It uses no labels and was fit only on data before E1. Saved as `models/leak_model_v2.joblib`. There is no "trained on all four events" final model, because this model does not use labels.
- Top features by permutation importance on the held-out blocks: mean_loaded_run_min (0.0316), Reservoirs_mean10 (0.0144), Oil_temperature_mean10 (0.0095), TP3_mean10 (0.0091), Motor_current_mean10 (0.0038), recharge_bar_per_min (0.0017), cycles_per_h (0.0006), TP2_mean10 (0.0003), load_duty (-0.0006), mean_off_min (-0.0009).

### How far to trust this

- **Optimistic.** Theta was chosen on the same folds shown here and sits at the top of the grid. Four events cannot support an independent threshold. There is no untouched test.
- **Brief signal.** The alert fires at some point in each event, but it is on for only 2 % to 26 % of event minutes. First alerts come 10 to 364 min after the start. It is not a continuous indicator, and most minutes of a real leak show no flag.
- **False alarms** are measured only in the +- 3 day blocks, not across the seven months. In the E1 fold, part of that block overlaps the model's training period.
- **Rates.** During a leak the compressor rarely unloads, so `leak_rate.estimate` rarely has a high-confidence value (4 of the 58 alert minutes in E4). Usually the hook falls back to `LEAK_MULTIPLIER`.
- **External test not run.** `data/MetroPT2.csv` is not on this machine. `external_test.py` skips cleanly and has not been run on the real file, so its column mapping for that file is untested.
- **Proxy.** A metro compressor, not a loco. A leak rate measured there is not a loco leak rate. The hook only demonstrates the mechanism.

### Advisor hook (`failover/app/backend.py`, `_leak_hook`)

Flag with a high-confidence rate: the leak range is raised to at least that rate. Flag with no rate: `LEAK_MULTIPLIER`. INVALID data: every value becomes the highest leak rate in the config, with the card line "compressor data invalid - using cautious air estimate". The hook can only raise the leak rate, so it never makes the air clock more optimistic (tested). The harness does not use it, and its 144-run summary is unchanged.

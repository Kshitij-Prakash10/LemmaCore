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

Downloaded and logged in `data/README.md`. The leak fit and anomaly detector are not built yet.

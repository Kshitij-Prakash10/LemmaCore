# Study sheet: ML and the app

Updated 14:58 from `docs/ml.md`, `models/metrics.json` (core 0.1, seed 7) and `docs/STATUS_B.md`. All metrics are on held-out **simulated** data. **[PENDING]** marks what was not built at 14:53.

## In one sentence
A classifier names which faults are present from noisy sensor windows, so the pilot does not need to know which unit failed. An offline app puts the advisor, the coverage map and the assumptions on one laptop. Real metro compressor data (MetroPT-3) is downloaded, but the real-data analysis is not built yet.

## Five facts to know (and where they come from)
1. **Training data comes from our core, never separate physics.** 60 s windows of **observed** signals from `failover.core.simulate`. 37 fault sets (healthy, 8 singles, 28 pairs) x 40 random scenarios. Randomized: ambient 20 to 48 C, gradient 0 to 3 percent, load, 2 or 3 units, distance, speed, noise 0 to 0.1, and plus or minus 20 percent on five physics parameters (domain randomization). 4,224 training windows. Source: `docs/ml.md`.
2. **Model and split.** One gradient-boosting classifier per fault (scikit-learn HistGradientBoosting). Split by scenario seed (20 percent held out), and 4 fault pairs never seen in training. About 14 ms per prediction. A single joint random forest found 0 of 4 unseen pairs; one model per fault found 2 of 4, so we use that. Source: `docs/ml.md`.
3. **Results (held out, after the fault).** Exact fault set right 55 percent of the time; micro precision 0.81, recall 0.73. Stuck temperature sensor: precision 1.0, recall 1.0. U2_TRIP 1.0 / 1.0. Accuracy falls gently with noise (0.71 at no noise, 0.63 at 0.1) and is 0.69 with parameters outside the training range. Source: `models/metrics.json`.
4. **The honest limit.** STANDBY_STUCK, MCB_TRIP and U1_TRIP plus STANDBY_STUCK all mean "unit 1 lost, loads not moved", so their signals are identical and no model can separate them (precision about 0.4 to 0.55). The advisor treats them the same, so it does not matter for the decision. COMPRESSOR_FAIL is often missed in the first minute because the pressure has barely moved. Source: `docs/ml.md`.
5. **Safety and the app.** The advisor uses the diagnosis only at 60 percent confidence or more with a named fault; otherwise it infers from the signals (the cautious path) and the screen says so. The app is Flask plus plain HTML, CSS and JavaScript, with no CDN, and works with Wi-Fi off. Tabs: Advisor, Coverage map, Real data, Assumptions, Report. 38 tests pass, including app tests with the network blocked. Source: `docs/STATUS_B.md`.

## Three hard questions and answers (no reading from a screen)
1. **Q: Your classifier is trained on your own simulator. Isn't it just learning your model?** A: Yes. It shows how well we can invert our simulator, not how it would do on a real loco. We tested it on fault pairs it never saw (2 of 4 found fully) and on parameters 20 to 30 percent outside the training range (accuracy 0.69). Real use needs retraining on real fault logs.
2. **Q: 55 percent is low.** A: That is the exact set of all faults. Most misses are faults that are physically indistinguishable in the signals (standby stuck versus MCB trip), and the advisor handles those the same way. Per fault, most are above 0.85 precision. Below 60 percent confidence, the advisor does not use the diagnosis at all.
3. **Q: Why a metro train dataset?** A: There is no public Indian loco fault data. MetroPT-3 is real, labelled compressor data from a metro train in Porto. We downloaded it, but the leak fit and anomaly detector were not finished at 14:53, so we make no real-data claim. **[PENDING: update if the Real data tab shows a result.]**

## What I do not know, and how I will say so
- Any real-loco accuracy: "We only have simulated test results."
- MetroPT-3 results, until `models/anomaly_metrics.json` or `data/processed/air_params_fit.json` exists.
- The minutes-left surrogate (stretch) was not built; `minutes_left_p5` returns None.

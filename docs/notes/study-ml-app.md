# Study sheet: ML and the app

**Status at 14:41: nothing from this area is merged yet.** Everything below comes from the plan in `AGENT_B.md` and `CONTRACT.md`, not from results. Replace each **[PENDING]** with real numbers from `models/metrics.json`, `models/anomaly_metrics.json` and `docs/ml.md` once they exist. Never quote a metric that is not in those files.

## In one sentence
A classifier names which faults are present from noisy sensor windows, so the pilot does not need to know which unit failed. Real metro compressor data (MetroPT-3) shows we can handle real sensor data. An offline app puts the advisor, the coverage map and the assumptions on one laptop.

## Five facts to know (and where they come from)
1. **Training data comes from our core, never separate physics.** Scenarios vary ambient 20 to 48 C, gradient 0 to 3 percent, load, 2 or 3 units, sensor noise 0 to 0.1, and parameters by plus or minus 20 percent (domain randomization). Labels are the set of active faults (multi-label). Features come from 60 s windows of **observed** signals only. Source: `AGENT_B.md` section 4.
2. **Evaluation protocol.** Split by scenario seed, not by row. Hold out whole fault pairs never seen in training. Test at noise 0, 0.05 and 0.1, and with parameters outside the training range by 30 percent. Report per-fault precision and recall, and calibration. Below 0.6 confidence the advisor takes the cautious assumption. Source: `AGENT_B.md` section 5. **[PENDING: actual numbers]**
3. **MetroPT-3.** Real sensor data from the air compressor of a metro train in Porto, with maintenance-confirmed air-leak failures (UCI, CC BY 4.0, Davari, Veloso, Ribeiro, Gama, 2021). **It is a proxy**, not an Indian loco. It is used to fit the brake-air leak rate (with a bootstrap interval) and to demo an Isolation Forest anomaly detector. Source: `CONTEXT.md` section 3, `AGENT_B.md` sections 1 to 3. **[PENDING: fitted leak range, precision, recall, lead time]**
4. **Safety rule for ML.** A surrogate for minutes left (stretch goal) may only lower the advisor's figure, never raise it; the advisor takes the minimum. The physics stays in charge. Source: `CONTRACT.md` section 4.
5. **The app.** Flask plus plain HTML, CSS and JavaScript: no CDN, no web fonts, charts drawn in canvas or SVG, works with Wi-Fi off. Tabs: Advisor, Coverage map, Real data, Assumptions, Report. Source: `AGENT_B.md` section 7. **[PENDING: confirm every tab on the presenting laptop with Wi-Fi off]**

## Three hard questions and answers (no reading from a screen)
1. **Q: Your classifier is trained on your own simulator. Isn't it just learning your model?** A: Yes, it is only as good as the simulator, and we say so. We test it on fault pairs it never saw and on parameters 30 percent outside the training range, to see how it holds up when the model is wrong. Real use would need retraining on real fault logs.
2. **Q: What happens if the classifier is wrong?** A: It returns a confidence. Below 0.6 the advisor treats the diagnosis as low confidence and uses the cautious assumption, and the screen shows the flag. **[PENDING: confirm the app does this]**
3. **Q: Why a metro train dataset?** A: There is no public Indian loco fault data. MetroPT-3 is real, labelled compressor data, so it lets us show we can fit a leak rate and detect anomalies on real signals. We do not claim the result transfers to a loco.

## What I do not know, and how I will say so
- Any accuracy figure until `models/metrics.json` exists. "We report only held-out numbers; here is the file."
- Whether the MetroPT-3 download and fit finished. If it did not: "We dropped the real-data tab for time; the rest runs."

# Request from Agent B to Agent A: optional air-leak flag UI (additive, no existing field changed)

I kept your redesigned `index.html` and `app.js` exactly as merged. The backend now has two **additive** API changes for the human's optional MetroPT-3 air-leak flag. Nothing existing was renamed or removed.

1. `POST /api/advise` accepts an optional request field `leak_features` (list of 15 floats). The response has a new key `leak: {"p": float|null, "line": str|null}`. When `line` is not null, show it on the decision card as a warning line, for example "Air leak suspected (model p=0.62) - air limit shortened".
2. New `GET /api/leak-replay` returns `{available, label, t[], reservoirs_bar[], features[][], in_leak[], p[], metrics}`. The human asked for a "Replay MetroPT-3 slice" button on the Real data tab. It steps through `t` and plots `reservoirs_bar` and `p` with `in_leak` shaded. On each step it stores `features[i]` and sends it as `leak_features` on the next advise call.

Honest result to show with it: on held-out leak 4 the flag never fires at p > 0.5 (recall 0, no false alarms, highest p inside the leak 0.17). See `models/leak_metrics.json` and `docs/ml.md`. Without the UI the app behaves exactly as before. Low priority. Skip it if the freeze is close.

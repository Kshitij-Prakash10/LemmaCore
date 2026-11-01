"""Flask server for the Failover Guardian app. Offline: static files only, no CDN.

Run: python -m failover.app.server  (http://127.0.0.1:5000)
"""
from __future__ import annotations

import os

from flask import Flask, jsonify, request, send_file, send_from_directory

from failover.app import backend

STATIC = os.path.join(os.path.dirname(__file__), "static")


def create_app() -> Flask:
    """Build the Flask app."""
    app = Flask(__name__, static_folder=None)

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.get("/static/<path:name>")
    def static_file(name: str):
        return send_from_directory(STATIC, name)

    @app.get("/api/status")
    def status():
        return jsonify({"core_version": backend.CORE_VERSION, "stub": backend.USING_STUB,
                        "classifier": os.path.exists(os.path.join(backend.ROOT, "models", "fault_clf.joblib"))})

    @app.get("/api/config")
    def config():
        cfg = backend.load_config()
        return jsonify({"config": cfg, "assumptions": backend.flatten_assumptions(cfg)})

    @app.post("/api/advise")
    def advise():
        return jsonify(backend.run_case(request.get_json(force=True) or {}))

    @app.post("/api/diagnose")
    def diagnose():
        body = request.get_json(force=True) or {}
        return jsonify(backend.diagnose(body.get("observed", body)))

    @app.get("/api/coverage")
    def coverage():
        return jsonify(backend.coverage())

    @app.get("/api/anomaly-demo")
    def anomaly_demo():
        demo = backend.read_json("data/processed/anomaly_demo.json")
        metrics = backend.read_json("models/anomaly_metrics.json")
        fit = backend.read_json("data/processed/air_params_fit.json")
        return jsonify({"available": demo is not None, "demo": demo, "metrics": metrics, "air_fit": fit})

    @app.get("/api/leak-replay")
    def leak_replay():
        from failover.ml.leak_detector import predict_proba
        r = backend.read_json("data/processed/leak_replay.json")
        if r is None:
            return jsonify({"available": False})
        r["p"] = [predict_proba(x) for x in r["features"]]
        r["metrics"] = backend.read_json("models/leak_metrics.json")
        r["available"] = True
        return jsonify(r)

    @app.get("/evidence")
    def evidence_page():
        return send_from_directory(STATIC, "evidence.html")

    @app.get("/api/evidence")
    def evidence():
        return jsonify({"metrics": backend.read_json("models/leak_v2_metrics.json"),
                        "external": backend.read_json("models/leak_v2_external.json"),
                        "replay": backend.read_json("data/processed/leak_replay_v2.json")})

    @app.get("/api/evidence/importance.svg")
    def evidence_importance():
        p = os.path.join(backend.ROOT, "models", "leak_v2_importance.svg")
        if not os.path.exists(p):
            return jsonify({"available": False}), 404
        return send_file(p, mimetype="image/svg+xml")

    @app.get("/api/metrics")
    def metrics():
        return jsonify({"available": True, "metrics": backend.read_json("models/metrics.json")})

    @app.get("/api/report")
    def report():
        p = next((c for c in (os.path.join(backend.ROOT, d, "report.html") for d in ("outputs", "demo_outputs"))
                  if os.path.exists(c)), "")
        if not p:
            return jsonify({"available": False, "reason": "run make harness to produce outputs/report.html"}), 404
        return send_file(p, as_attachment=request.args.get("download") == "1",
                         download_name="failover_guardian_report.html")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)

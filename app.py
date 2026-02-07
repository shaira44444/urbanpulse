import os
from flask import Flask, jsonify, Response, request

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

app = Flask(__name__)

@app.post("/alert")
def alert():
    payload = request.get_json(silent=True) or {}

    if DEMO_MODE:
        # Demo-safe behavior
        return jsonify({
            "status": "demo_mode_alert_logged",
            "note": "No external systems were triggered",
            "received": payload
        })

    # Live mode (future / watsonx / Xero)
    # from xero_client import send_alert_to_xero
    # result = send_alert_to_xero(payload)

    return jsonify({
        "status": "alert_triggered",
        "received": payload
    })

@app.get("/")
def home():
    return {"message": "URBANPULSE is running", "endpoints": ["/health", "/snapshot", "/log", "/alert"]}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/snapshot")
def snapshot():
    from nea_agent import run_snapshot  # lazy import
    return jsonify(run_snapshot())

@app.get("/log")
def log():
    from nea_agent import run_snapshot, format_like_colab  # lazy import
    snap = run_snapshot()
    text = format_like_colab(snap)
    return Response(text, mimetype="text/plain")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)

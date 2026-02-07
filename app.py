import os
import socket
import time
from flask import Flask, jsonify, Response, request

app = Flask(__name__)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def is_demo_mode() -> bool:
    """
    Read DEMO_MODE at request-time (not only at startup),
    so you don't need to restart the server to reflect changes.
    """
    return os.getenv("DEMO_MODE", "false").strip().lower() in ("1", "true", "yes", "y", "on")

# Fingerprint this running process so you can prove which instance handled a request.
INSTANCE = {
    "pid": os.getpid(),
    "host": socket.gethostname(),
    "started_at_epoch": int(time.time()),
    "file": __file__,
}

# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.get("/config")
def config():
    return jsonify({
        "DEMO_MODE": is_demo_mode(),
        "instance": INSTANCE,
        "port_env": os.getenv("PORT", "8080"),
    })


@app.post("/alert")
def alert():
    payload = request.get_json(silent=True) or {}

    if is_demo_mode():
        # Demo-safe behavior: do NOT call external systems
        return jsonify({
            "status": "demo_mode_alert_logged",
            "note": "No external systems were triggered",
            "instance": INSTANCE,
            "received": payload
        })

    # Live mode (future / watsonx / Xero)
    # from xero_client import send_alert_to_xero
    # result = send_alert_to_xero(payload)

    return jsonify({
        "status": "alert_triggered",
        "instance": INSTANCE,
        "received": payload
    })


@app.get("/")
def home():
    return jsonify({
        "message": "URBANPULSE is running",
        "demo_mode": is_demo_mode(),
        "instance": INSTANCE,
        "endpoints": ["/health", "/snapshot", "/log", "/alert", "/config"]
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "demo_mode": is_demo_mode(),
        "instance": INSTANCE
    })


@app.get("/snapshot")
def snapshot():
    from nea_agent import run_snapshot  # lazy import
    data = run_snapshot()
    # Optional: attach instance + demo flag for traceability
    return jsonify({
        "demo_mode": is_demo_mode(),
        "instance": INSTANCE,
        "data": data
    })


@app.get("/log")
def log():
    from nea_agent import run_snapshot, format_like_colab  # lazy import
    snap = run_snapshot()
    text = format_like_colab(snap)
    header = (
        f"URBANPULSE LOG\n"
        f"DEMO_MODE={is_demo_mode()}\n"
        f"INSTANCE={INSTANCE}\n"
        f"{'-'*60}\n"
    )
    return Response(header + text, mimetype="text/plain")


# ---------------------------------------------------------
# Local run
# ---------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"[UrbanPulse] Starting Flask on 0.0.0.0:{port} | DEMO_MODE={is_demo_mode()} | FILE={__file__}")
    app.run(host="0.0.0.0", port=port)

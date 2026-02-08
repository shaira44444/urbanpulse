import os
import socket
import time
import json
import random
# Force Render Rebuild - Final Role-Based Update
from flask import Flask, jsonify, Response, request, render_template, send_from_directory

# -----------------------------
# Config / flags
# -----------------------------
def is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "false").strip().lower() in ("1", "true", "yes", "y", "on")

INSTANCE = {
    "pid": os.getpid(),
    "host": socket.gethostname(),
    "started_at_epoch": int(time.time()),
    "file": __file__,
}

app = Flask(__name__)

# ==============================================================================
# GOD MODE: WSGI MIDDLEWARE (The Ultimate Bypass)
# ==============================================================================
class WatsonxBypassMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        
        # 1. TRAP THE SPECIFIC URL
        if path == '/api/watsonx-scenario':
            
            # A. HANDLE BROWSER TEST (GET)
            if environ['REQUEST_METHOD'] == 'GET':
                status = '200 OK'
                headers = [('Content-Type', 'application/json')]
                start_response(status, headers)
                return [b'{"status": "bypass_active", "message": "GOD MODE: Login Wall Destroyed."}']

            # B. HANDLE AI REQUEST (POST)
            if environ['REQUEST_METHOD'] == 'POST':
                try:
                    # Read JSON
                    try:
                        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
                    except (ValueError):
                        request_body_size = 0
                    
                    request_body = environ['wsgi.input'].read(request_body_size)
                    
                    if not request_body:
                        payload = {}
                    else:
                        payload = json.loads(request_body)
                        
                    raw_key = payload.get("scenario_key")
                    if raw_key is None:
                        raw_key = ""                    
                    # --- THE SECRET SHORTCUT: DETECT ROLE FROM KEY ---
                    # If key has "_public" (e.g. "severe_haze_public"), show User View.
                    # Otherwise, show Admin/Clinic View.
                    user_role = "admin"
                    if "_public" in raw_key:
                        user_role = "public"
                        raw_key = raw_key.replace("_public", "") # Remove suffix to find real data
                        
                    scenario_key = raw_key.strip().lower().replace(" ", "_")

                    # --- RUN LOGIC MANUALLY ---
                    from scenarios import DEMO_SCENARIOS
                    global AGENT_SYSTEM
                    
                    if AGENT_SYSTEM is None:
                        AGENT_SYSTEM = _build_agent_system()

                    # Check key
                    if not scenario_key or scenario_key not in DEMO_SCENARIOS:
                        status = '400 Bad Request'
                        headers = [('Content-Type', 'application/json')]
                        start_response(status, headers)
                        return [json.dumps({"status": "error", "message": f"Invalid key: {raw_key}"}).encode('utf-8')]

                    # GET THE BASE SCENARIO & ADD NOISE
                    base_scenario = DEMO_SCENARIOS[scenario_key]
                    live_scenario = base_scenario.copy()
                    live_psi = base_scenario["psi_data"].copy()
                    
                    for region in live_psi:
                        noise = random.randint(-4, 4) 
                        live_psi[region] += noise
                    live_scenario["psi_data"] = live_psi

                    # RUN SIMULATION
                    result = AGENT_SYSTEM.run_cycle(live_scenario)
                    
                    # --- SMART SUMMARY GENERATION (ROLE BASED) ---
                    risk_data = result.get('risk_assessment', {})
                    psi_val = risk_data.get('current_psi', 'Unknown')
                    risk_level = risk_data.get('risk_level', 'UNKNOWN')
                    regions_list = risk_data.get('affected_regions', [])
                    regions_str = ", ".join([r.capitalize() for r in regions_list]) if regions_list else "None"

                    # === BRANCHING LOGIC: PUBLIC vs CLINIC ===
                    
                    if user_role == "public":
                        # --- PUBLIC VIEW (Health Advice Only) ---
                        if risk_level == "LOW":
                            advice = "✅ Air quality is Good. It is safe to go outside and exercise."
                        elif risk_level == "MODERATE":
                            advice = "⚠️ Air quality is Moderate. Vulnerable groups should reduce outdoor exertion."
                        else: # Severe
                            advice = "⛔ HAZARDOUS HAZE. Please stay indoors, close windows, and wear an N95 mask if you must go out."

                        ai_summary = (
                            f"📢 PUBLIC ADVISORY: {scenario_key.replace('_', ' ').title()} Event.\n"
                            f"🌍 Current PSI: {psi_val} ({risk_level}).\n"
                            f"📍 Affected Areas: {regions_str}.\n"
                            f"💡 HEALTH ADVICE: {advice}"
                        )
                        
                    else:
                        # --- CLINIC/ADMIN VIEW (Supply Chain Data) ---
                        supply_data = result.get('supply_chain_actions', {})
                        po_id = supply_data.get('po_id', 'No PO')
                        total_cost = supply_data.get('total_value', '$0')
                        clinics_count = result.get('healthcare_alerts', {}).get('total_clinics', 0)
                        
                        if clinics_count > 0:
                            action_text = (
                                f"RESPONSE: Alert sent to {clinics_count} clinics in {regions_str}. "
                                f"Generated DRAFT Supply Order {po_id} (Value: {total_cost}). "
                                f"Awaiting validation from Clinic Managers."
                            )
                        else:
                            action_text = "RESPONSE: Monitoring mode active. No immediate intervention required."

                        ai_summary = (
                            f"🚨 COMMANDER REPORT: {scenario_key.replace('_', ' ').title()}. "
                            f"Risk Level: {risk_level}. "
                            f"Highest PSI: {psi_val}. "
                            f"{action_text}"
                        )

                    # ===================================
                    
                    response_data = {
                        "status": "success",
                        "scenario": scenario_key,
                        "ai_summary": ai_summary,
                        "raw_data": result
                    }
                    
                    status = '200 OK'
                    headers = [('Content-Type', 'application/json')]
                    start_response(status, headers)
                    return [json.dumps(response_data).encode('utf-8')]

                except Exception as e:
                    status = '500 Server Error'
                    headers = [('Content-Type', 'application/json')]
                    start_response(status, headers)
                    return [json.dumps({"status": "error", "message": str(e)}).encode('utf-8')]

        # 2. IF NOT OUR URL, LET FLASK HANDLE IT
        return self.app(environ, start_response)

app.wsgi_app = WatsonxBypassMiddleware(app.wsgi_app)
# ==============================================================================


# -----------------------------
# Website routes (Dashboard)
# -----------------------------
@app.get("/")
def home():
    return send_from_directory("static", "index.html")

@app.get("/config")
def config():
    return jsonify({
        "DEMO_MODE": is_demo_mode(),
        "instance": INSTANCE,
        "port_env": os.getenv("PORT", "8080"),
    })

# -----------------------------
# Scenario-based agent APIs
# -----------------------------
def _build_agent_system():
    from agents import (
        EnvironmentSentinel,
        ScalestackAgent,
        DynamiqMedicalAgent,
        HealthcarePreparednessAgent,
        SupplyChainAgent
    )
    sentinel = EnvironmentSentinel()
    sentinel.register_agent(ScalestackAgent())
    sentinel.register_agent(DynamiqMedicalAgent())
    sentinel.register_agent(HealthcarePreparednessAgent())
    sentinel.register_agent(SupplyChainAgent())
    return sentinel

AGENT_SYSTEM = None

@app.get("/api/scenarios")
def list_scenarios():
    from scenarios import DEMO_SCENARIOS
    scenarios = [
        {"key": k, "description": v.get("description", ""), "psi_data": v.get("psi_data", {})}
        for k, v in DEMO_SCENARIOS.items()
    ]
    return jsonify({"scenarios": scenarios})

@app.post("/api/run-scenario/<scenario_key>")
def run_scenario(scenario_key: str):
    global AGENT_SYSTEM
    from scenarios import DEMO_SCENARIOS
    import random 

    if scenario_key == "normal" or scenario_key == "normal_air_quality":
        scenario_key = "low_haze"

    if scenario_key not in DEMO_SCENARIOS:
        return jsonify({"error": f"Unknown scenario '{scenario_key}'"}), 404

    if AGENT_SYSTEM is None:
        AGENT_SYSTEM = _build_agent_system()

    base_scenario = DEMO_SCENARIOS[scenario_key]
    live_scenario = base_scenario.copy()
    live_psi = base_scenario["psi_data"].copy()
    
    for region in live_psi:
        noise = random.randint(-4, 4) 
        live_psi[region] += noise
    
    live_scenario["psi_data"] = live_psi

    result = AGENT_SYSTEM.run_cycle(live_scenario)
    result["_meta"] = {"demo_mode": is_demo_mode(), "instance": INSTANCE}
    return jsonify(result)

# -----------------------------
# Existing live-data endpoints
# -----------------------------
@app.get("/health")
def health():
    return jsonify({"status": "ok", "demo_mode": is_demo_mode(), "instance": INSTANCE})

@app.get("/snapshot")
def snapshot():
    from nea_agent import run_snapshot
    data = run_snapshot()
    return jsonify({"demo_mode": is_demo_mode(), "instance": INSTANCE, "data": data})

@app.get("/log")
def log():
    from nea_agent import run_snapshot, format_like_colab
    snap = run_snapshot()
    text = format_like_colab(snap)
    header = (
        f"URBANPULSE LOG\n"
        f"DEMO_MODE={is_demo_mode()}\n"
        f"INSTANCE={INSTANCE}\n"
        f"{'-'*60}\n"
    )
    return Response(header + text, mimetype="text/plain")

@app.post("/alert")
def alert():
    payload = request.get_json(silent=True) or {}
    if is_demo_mode():
        return jsonify({
            "status": "demo_mode_alert_logged",
            "note": "No external systems were triggered",
            "instance": INSTANCE,
            "received": payload
        })
    return jsonify({
        "status": "alert_triggered",
        "instance": INSTANCE,
        "received": payload
    })

# -----------------------------
# CLINIC DEMO ROUTES
# -----------------------------
@app.route("/clinic")
def clinic_dashboard():
    return send_from_directory("static", "clinic.html")

@app.get("/api/clinic-poll")
def clinic_poll():
    global AGENT_SYSTEM
    if AGENT_SYSTEM is None:
        return jsonify({"status": "waiting"})

    memory = AGENT_SYSTEM.memory
    if not memory:
        return jsonify({"status": "waiting"})

    last_cycle = memory[-1]
    alert_data = last_cycle.get("healthcare_alerts", {})
    supply_data = last_cycle.get("supply_chain_actions", {})
    
    if not alert_data:
        return jsonify({"status": "waiting"})
        
    return jsonify({
        "status": "alert_active",
        "psi": last_cycle.get("risk_assessment", {}).get("current_psi", 0),
        "risk_level": last_cycle.get("risk_assessment", {}).get("risk_level", "UNKNOWN"),
        "recommended_masks": supply_data.get("order_details", {}).get("n95_masks", 0),
        "alert_message": alert_data.get("alert_message", "No message")
    })

@app.post("/api/clinic-confirm-order")
def confirm_order():
    data = request.json
    final_qty = data.get("confirmed_qty")
    print(f"✅ CLINIC CONFIRMED ORDER: {final_qty} Masks")
    return jsonify({"status": "success", "message": f"Order for {final_qty} masks processed."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"[UrbanPulse] Starting on 0.0.0.0:{port} | DEMO_MODE={is_demo_mode()} | FILE={__file__}")
    app.run(host="0.0.0.0", port=port)

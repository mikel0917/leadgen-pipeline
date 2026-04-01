"""Flask API wrapping all pipeline scripts. n8n calls these endpoints via HTTP."""
import json
import logging
import sys
from pathlib import Path

from flask import Flask, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.parse_voter_file import parse_voter_file, save_leads
from scripts.enrich_lead import enrich_lead, enrich_batch
from scripts.verify_email import verify_email, verify_batch
from scripts.score_leads import score_batch
from scripts.send_outreach import send_email, send_batch
from scripts.export_csv import export_all_tiers, export_daily_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "leadgen-pipeline-v1"})


@app.route("/parse", methods=["POST"])
def parse():
    """Parse voter file and return raw leads. Accepts optional overrides in body."""
    data = request.get_json(silent=True) or {}
    leads = parse_voter_file(
        state=data.get("state"),
        cities=data.get("cities"),
        zips=data.get("zips"),
        min_age=data.get("min_age"),
        max_age=data.get("max_age"),
        limit=data.get("limit"),
    )
    path = save_leads(leads)
    return jsonify({"count": len(leads), "file": path, "leads": leads})


@app.route("/enrich", methods=["POST"])
def enrich():
    """Enrich a single lead or batch. Send {lead: {...}} or {leads: [...]}."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    if "lead" in data:
        result = enrich_lead(data["lead"])
        return jsonify({"lead": result})
    elif "leads" in data:
        results = enrich_batch(data["leads"])
        return jsonify({"count": len(results), "leads": results})
    return jsonify({"error": "Provide 'lead' or 'leads' in body"}), 400


@app.route("/verify", methods=["POST"])
def verify():
    """Verify email(s). Send {email: "..."} or {emails: [...]}."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    if "email" in data:
        result = verify_email(data["email"])
        return jsonify(result)
    elif "emails" in data:
        results = verify_batch(data["emails"])
        return jsonify({"count": len(results), "results": results})
    return jsonify({"error": "Provide 'email' or 'emails'"}), 400


@app.route("/score", methods=["POST"])
def score():
    """Score a batch of leads. Send {leads: [...]}."""
    data = request.get_json()
    if not data or "leads" not in data:
        return jsonify({"error": "Provide 'leads' array"}), 400
    scored = score_batch(data["leads"])
    tier_counts = {}
    for l in scored:
        t = l.get("lead_tier", "?")
        tier_counts[t] = tier_counts.get(t, 0) + 1
    return jsonify({"count": len(scored), "tiers": tier_counts, "leads": scored})


@app.route("/outreach", methods=["POST"])
def outreach():
    """Send outreach email. {lead: {...}} or {leads: [...]}."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    if "lead" in data:
        result = send_email(data["lead"])
        return jsonify(result)
    elif "leads" in data:
        results = send_batch(data["leads"])
        sent = sum(1 for r in results if r["success"])
        return jsonify({"total": len(results), "sent": sent, "results": results})
    return jsonify({"error": "Provide 'lead' or 'leads'"}), 400


@app.route("/webhook/interest", methods=["POST"])
def webhook_interest():
    """Receive interest signal from landing page form (Tally.so webhook)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    app.logger.info("Interest webhook received: %s", json.dumps(data))
    return jsonify({"status": "received", "data": data})


@app.route("/export", methods=["GET", "POST"])
def export():
    """Generate and return today's tier CSVs."""
    data = request.get_json(silent=True) or {}
    leads = data.get("leads", [])
    if not leads:
        return jsonify({"error": "Provide 'leads' array or call with today's data"}), 400
    results = export_all_tiers(leads)
    summary_path = export_daily_summary(leads)
    return jsonify({
        "tiers": {t: {"path": r["path"], "count": r["count"]} for t, r in results.items()},
        "summary": summary_path,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

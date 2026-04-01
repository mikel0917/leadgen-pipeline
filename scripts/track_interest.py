"""Stage 5: Track interest signals from landing page forms and callbacks."""
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.scoring_model import TIER_THRESHOLDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"[^\d]", "", str(phone))
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return digits


def normalize_email(email: str) -> str:
    return str(email).strip().lower() if email else ""


def match_to_lead(submission: dict, leads: list[dict]) -> dict | None:
    sub_phone = normalize_phone(submission.get("phone", ""))
    sub_email = normalize_email(submission.get("email", ""))
    sub_name = str(submission.get("name", "")).strip().lower()

    for lead in leads:
        lead_phone = normalize_phone(lead.get("phone", ""))
        lead_email = normalize_email(lead.get("email", ""))
        lead_name = lead.get("full_name", "").strip().lower()

        if sub_phone and lead_phone and sub_phone == lead_phone:
            log.info("Matched by phone: %s → %s", sub_phone, lead.get("full_name"))
            return lead

        if sub_email and lead_email and sub_email == lead_email:
            log.info("Matched by email: %s → %s", sub_email, lead.get("full_name"))
            return lead

        if sub_name and lead_name and sub_name == lead_name:
            log.info("Matched by name: %s", lead.get("full_name"))
            return lead

    log.warning("No match found for submission: %s", submission)
    return None


def process_interest(submission: dict, leads: list[dict], channel: str = "landing_page_form") -> dict:
    result = {
        "matched": False,
        "lead_name": None,
        "previous_tier": None,
        "new_tier": None,
        "upgraded": False,
        "timestamp": datetime.now().isoformat(),
    }

    lead = match_to_lead(submission, leads)
    if not lead:
        result["error"] = "No matching lead found"
        return result

    result["matched"] = True
    result["lead_name"] = lead.get("full_name")
    result["previous_tier"] = lead.get("lead_tier")

    lead["interest_expressed"] = "YES"
    lead["interest_channel"] = channel
    lead["date_qualified"] = datetime.now().strftime("%Y-%m-%d")

    score = lead.get("lead_score", 0)
    if score >= TIER_THRESHOLDS["A"]["min_score"]:
        if lead.get("lead_tier") != "A":
            result["upgraded"] = True
            result["previous_tier"] = lead.get("lead_tier")
        lead["lead_tier"] = "A"

    result["new_tier"] = lead["lead_tier"]

    log.info("Interest recorded: %s → Tier %s (upgraded=%s, channel=%s)",
             lead.get("full_name"), lead["lead_tier"], result["upgraded"], channel)

    return result


def process_tally_webhook(payload: dict, leads: list[dict]) -> dict:
    """Parse a Tally.so webhook payload and process interest."""
    fields = payload.get("data", {}).get("fields", [])
    submission = {}
    for field in fields:
        label = str(field.get("label", "")).lower()
        value = field.get("value", "")
        if "name" in label:
            submission["name"] = value
        elif "email" in label:
            submission["email"] = value
        elif "phone" in label:
            submission["phone"] = value

    if not submission:
        submission = {
            "name": payload.get("name", ""),
            "email": payload.get("email", ""),
            "phone": payload.get("phone", ""),
        }

    return process_interest(submission, leads, channel="landing_page_form")


def process_call_result(call_data: dict, leads: list[dict]) -> dict:
    """Process a callback from the AI voice caller (Pipecat/Bland)."""
    interested = str(call_data.get("interest_status", "")).lower() in ("yes", "interested", "true")
    if not interested:
        log.info("Call result: not interested — %s", call_data.get("phone"))
        return {"matched": False, "interested": False}

    submission = {
        "phone": call_data.get("phone", ""),
        "name": call_data.get("lead_name", ""),
    }
    return process_interest(submission, leads, channel="ai_voice_call")


if __name__ == "__main__":
    test_leads = [
        {"full_name": "Jose Alvarez", "email": "jose@test.com", "phone": "+13055551234",
         "lead_score": 95, "lead_tier": "B"},
        {"full_name": "Jane Doe", "email": "jane@test.com", "phone": "+13055555678",
         "lead_score": 45, "lead_tier": "C"},
    ]
    test_submission = {"name": "Jose Alvarez", "email": "jose@test.com", "phone": "305-555-1234"}
    result = process_interest(test_submission, test_leads)
    print(json.dumps(result, indent=2))
    print("Updated lead:", json.dumps(test_leads[0], indent=2))

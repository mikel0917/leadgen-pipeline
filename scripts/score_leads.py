"""Stage 3: Score leads based on demographic criteria and assign quality tiers."""
import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.scoring_model import SCORING_WEIGHTS, TIER_THRESHOLDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def calculate_score(lead: dict) -> int:
    score = 0
    age = lead.get("age")
    if age:
        if 55 <= age <= 75:
            score += SCORING_WEIGHTS["age_55_75"]
        elif (45 <= age < 55) or (76 <= age <= 85):
            score += SCORING_WEIGHTS["age_45_54_or_76_85"]

    vet = str(lead.get("veteran_status", "")).lower()
    if vet in ("confirmed", "yes", "true"):
        score += SCORING_WEIGHTS["veteran_confirmed"]
    elif vet == "likely":
        score += SCORING_WEIGHTS["veteran_zip_proxy"]

    marital = str(lead.get("marital_status", "")).lower()
    if marital in ("married", "m"):
        score += SCORING_WEIGHTS["married"]

    homeowner = str(lead.get("homeowner", "")).lower()
    if homeowner in ("yes", "true", "owner"):
        score += SCORING_WEIGHTS["homeowner"]

    if lead.get("recent_home_purchase"):
        score += SCORING_WEIGHTS["recent_home_purchase"]

    if lead.get("recent_marriage"):
        score += SCORING_WEIGHTS["recent_marriage"]

    if lead.get("email"):
        score += SCORING_WEIGHTS["has_email"]

    if lead.get("phone"):
        score += SCORING_WEIGHTS["has_phone"]

    if lead.get("target_city_match", True):
        score += SCORING_WEIGHTS["target_city_match"]

    if lead.get("prior_insurance_signal"):
        score += SCORING_WEIGHTS["prior_insurance_signal"]

    if str(lead.get("interest_expressed", "")).upper() == "YES":
        score += SCORING_WEIGHTS["expressed_interest"]

    return score


def assign_tier(score: int, interest_expressed: bool = False) -> str:
    if score >= TIER_THRESHOLDS["A"]["min_score"] and interest_expressed:
        return "A"
    if score >= TIER_THRESHOLDS["B"]["min_score"]:
        return "B"
    if score >= TIER_THRESHOLDS["C"]["min_score"]:
        return "C"
    return "D"


def score_lead(lead: dict) -> dict:
    score = calculate_score(lead)
    interested = str(lead.get("interest_expressed", "")).upper() == "YES"
    tier = assign_tier(score, interested)
    lead["lead_score"] = score
    lead["lead_tier"] = tier
    lead["date_scored"] = date.today().isoformat()
    return lead


def score_batch(leads: list[dict]) -> list[dict]:
    log.info("Scoring %d leads", len(leads))
    scored = [score_lead(lead) for lead in leads]
    scored.sort(key=lambda l: l["lead_score"], reverse=True)

    tier_counts = {}
    for lead in scored:
        t = lead["lead_tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1

    log.info("Scoring complete. Distribution: %s", tier_counts)
    for tier, count in sorted(tier_counts.items()):
        log.info("  Tier %s: %d leads", tier, count)

    return scored


if __name__ == "__main__":
    test_leads = [
        {"full_name": "Jose Alvarez", "age": 65, "marital_status": "Married",
         "veteran_status": "Confirmed", "email": "jose@email.com", "phone": "+13055551234",
         "city": "Miami", "state": "FL"},
        {"full_name": "Jane Doe", "age": 50, "marital_status": "Single",
         "veteran_status": "Unknown", "email": "", "phone": "",
         "city": "Miami", "state": "FL"},
        {"full_name": "Bob Young", "age": 72, "marital_status": "Married",
         "veteran_status": "Unknown", "email": "bob@test.com", "phone": "",
         "city": "Miami", "state": "FL"},
    ]
    scored = score_batch(test_leads)
    for lead in scored:
        print(f"{lead['full_name']}: score={lead['lead_score']}, tier={lead['lead_tier']}")

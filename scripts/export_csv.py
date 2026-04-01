"""Stage 6: Export scored leads into tier-specific CSV files."""
import logging
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import OUTPUT_PATH
from config.scoring_model import TIER_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def export_tier_csv(leads: list[dict], tier: str, output_dir: str = None) -> str | None:
    output_dir = output_dir or OUTPUT_PATH
    os.makedirs(output_dir, exist_ok=True)

    tier_leads = [l for l in leads if l.get("lead_tier") == tier]
    if not tier_leads:
        log.info("No Tier %s leads to export", tier)
        return None

    columns = TIER_COLUMNS.get(tier, TIER_COLUMNS["D"])
    df = pd.DataFrame(tier_leads)

    available = [c for c in columns if c in df.columns]
    missing = [c for c in columns if c not in df.columns]
    if missing:
        for col in missing:
            df[col] = ""
        available = columns

    df = df[available]
    filename = f"tier_{tier.lower()}_{date.today().isoformat()}.csv"
    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False)
    log.info("Exported %d Tier %s leads to %s", len(tier_leads), tier, filepath)
    return filepath


def export_all_tiers(leads: list[dict], output_dir: str = None) -> dict:
    results = {}
    for tier in ["A", "B", "C", "D"]:
        path = export_tier_csv(leads, tier, output_dir)
        if path:
            count = sum(1 for l in leads if l.get("lead_tier") == tier)
            results[tier] = {"path": path, "count": count}

    log.info("Export summary: %s", {t: r["count"] for t, r in results.items()})
    return results


def export_daily_summary(leads: list[dict], output_dir: str = None) -> str:
    output_dir = output_dir or OUTPUT_PATH
    os.makedirs(output_dir, exist_ok=True)

    summary = {
        "date": date.today().isoformat(),
        "total_leads": len(leads),
        "tier_a": sum(1 for l in leads if l.get("lead_tier") == "A"),
        "tier_b": sum(1 for l in leads if l.get("lead_tier") == "B"),
        "tier_c": sum(1 for l in leads if l.get("lead_tier") == "C"),
        "tier_d": sum(1 for l in leads if l.get("lead_tier") == "D"),
        "with_email": sum(1 for l in leads if l.get("email")),
        "with_phone": sum(1 for l in leads if l.get("phone")),
        "interested": sum(1 for l in leads if str(l.get("interest_expressed", "")).upper() == "YES"),
    }

    filepath = os.path.join(output_dir, f"summary_{date.today().isoformat()}.csv")
    pd.DataFrame([summary]).to_csv(filepath, index=False)
    log.info("Daily summary: %s", summary)
    return filepath


if __name__ == "__main__":
    test_leads = [
        {"full_name": "Jose Alvarez", "age": 65, "city": "Miami", "state": "FL",
         "zip_code": "33101", "lead_score": 110, "lead_tier": "A",
         "interest_expressed": "YES", "interest_channel": "email_click",
         "email": "jose@test.com", "phone": "+13055551234",
         "marital_status": "Married", "veteran_status": "Confirmed",
         "date_sourced": "2026-03-29"},
        {"full_name": "Jane Doe", "age": 50, "city": "Miami", "state": "FL",
         "zip_code": "33102", "lead_score": 45, "lead_tier": "C",
         "email": "jane@test.com", "date_sourced": "2026-03-29"},
        {"full_name": "Bob Young", "age": 72, "city": "Miami", "state": "FL",
         "zip_code": "33103", "lead_score": 20, "lead_tier": "D",
         "date_sourced": "2026-03-29"},
    ]
    results = export_all_tiers(test_leads)
    for tier, info in results.items():
        print(f"Tier {tier}: {info['count']} leads → {info['path']}")

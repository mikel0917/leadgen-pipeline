"""
main.py — Run the full LeadGen pipeline end to end.

Usage:
    python main.py                        # uses settings from .env
    python main.py --state NC --limit 50  # override via CLI
"""
import argparse
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def run_pipeline(state=None, cities=None, limit=None):
    from scripts.parse_voter_file import parse_voter_file, save_leads
    from scripts.enrich_lead import enrich_batch
    from scripts.verify_email import verify_batch
    from scripts.score_leads import score_batch
    from scripts.export_csv import export_all_tiers, export_daily_summary

    log.info("=== LeadGen Pipeline Starting ===")

    # Stage 1: Parse
    log.info("Stage 1: Parsing voter file...")
    leads = parse_voter_file(state=state, cities=cities, limit=limit)
    if not leads:
        log.error("No leads parsed. Check VOTER_FILE_PATH and filters.")
        return

    # Stage 2: Enrich
    log.info("Stage 2: Enriching %d leads...", len(leads))
    leads = enrich_batch(leads)

    # Stage 2b: Verify emails
    emails = [l["email"] for l in leads if l.get("email")]
    if emails:
        log.info("Stage 2b: Verifying %d emails...", len(emails))
        verified = {r["email"]: r for r in verify_batch(emails)}
        for lead in leads:
            if lead.get("email"):
                v = verified.get(lead["email"], {})
                if v.get("score", 0) < 30:
                    lead["email"] = ""  # drop bad emails

    # Stage 3: Score
    log.info("Stage 3: Scoring leads...")
    leads = score_batch(leads)

    # Stage 4: Export
    log.info("Stage 4: Exporting CSVs...")
    results = export_all_tiers(leads)
    export_daily_summary(leads)

    log.info("=== Pipeline Complete ===")
    for tier, info in results.items():
        log.info("  Tier %s: %d leads → %s", tier, info["count"], info["path"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LeadGen Pipeline")
    parser.add_argument("--state", help="State code (e.g. NC, FL)")
    parser.add_argument("--cities", help="Comma-separated cities")
    parser.add_argument("--limit", type=int, help="Max leads to process")
    args = parser.parse_args()

    cities = args.cities.split(",") if args.cities else None
    run_pipeline(state=args.state, cities=cities, limit=args.limit)

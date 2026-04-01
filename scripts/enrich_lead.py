"""Stage 2: Enrich leads by scraping free people-search sites for contact info."""
import json
import logging
import re
import time
import sys
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import SCRAPE_DELAY_SECONDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_truepeoplesearch(name: str, city: str, state: str) -> dict:
    """Attempt to find contact info via TruePeopleSearch. Returns dict with phone/email or empty."""
    result = {"phone": "", "email": "", "source": "truepeoplesearch", "relatives": []}
    try:
        query = quote_plus(f"{name} {city} {state}")
        url = f"https://www.truepeoplesearch.com/results?name={query}"
        resp = requests.get(url, headers=HEADERS, timeout=15)

        if resp.status_code != 200:
            log.warning("TruePeopleSearch returned %d for %s", resp.status_code, name)
            return result

        soup = BeautifulSoup(resp.text, "html.parser")

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "ProfilePage":
                    person = data.get("mainEntity", {})

                    phones = person.get("telephone", [])
                    if isinstance(phones, str):
                        phones = [phones]
                    if phones:
                        raw = re.sub(r"[^\d]", "", phones[0])
                        if len(raw) == 10:
                            result["phone"] = f"+1{raw}"
                        elif len(raw) == 11 and raw.startswith("1"):
                            result["phone"] = f"+{raw}"

                    email_field = person.get("email", "")
                    if isinstance(email_field, list) and email_field:
                        email_field = email_field[0]
                    if email_field and "@" in str(email_field):
                        result["email"] = str(email_field).strip().lower()

                    relatives = person.get("relatedTo", [])
                    result["relatives"] = [r.get("name", "") for r in relatives[:5]]
                    break
            except (json.JSONDecodeError, TypeError):
                continue

    except requests.RequestException as e:
        log.warning("TruePeopleSearch request failed for %s: %s", name, e)

    return result


def scrape_fastpeoplesearch(name: str, city: str, state: str) -> dict:
    """Fallback: attempt FastPeopleSearch for contact info."""
    result = {"phone": "", "email": "", "source": "fastpeoplesearch", "relatives": []}
    try:
        name_slug = name.lower().replace(" ", "-")
        city_slug = city.lower().replace(" ", "-")
        url = f"https://www.fastpeoplesearch.com/name/{name_slug}_{city_slug}-{state.lower()}"
        resp = requests.get(url, headers=HEADERS, timeout=15)

        if resp.status_code != 200:
            log.warning("FastPeopleSearch returned %d for %s", resp.status_code, name)
            return result

        soup = BeautifulSoup(resp.text, "html.parser")

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Person":
                    phone = data.get("telephone", "")
                    if phone:
                        raw = re.sub(r"[^\d]", "", str(phone))
                        if len(raw) == 10:
                            result["phone"] = f"+1{raw}"

                    email = data.get("email", "")
                    if email and "@" in str(email):
                        result["email"] = str(email).strip().lower()
                    break
            except (json.JSONDecodeError, TypeError):
                continue

    except requests.RequestException as e:
        log.warning("FastPeopleSearch request failed for %s: %s", name, e)

    return result


def enrich_lead(lead: dict) -> dict:
    """Enrich a single lead with phone and email from people-search sites."""
    name = lead.get("full_name", "")
    city = lead.get("city", "")
    state = lead.get("state", "")

    if not name or not city:
        log.warning("Skipping enrichment — missing name or city: %s", lead)
        return lead

    existing_email = lead.get("email", "")
    existing_phone = lead.get("phone", "")

    if existing_email and existing_phone:
        log.info("Lead %s already has email + phone, skipping scrape", name)
        lead["enrichment_source"] = "voter_file"
        return lead

    tps = scrape_truepeoplesearch(name, city, state)
    time.sleep(SCRAPE_DELAY_SECONDS)

    if not tps["phone"] and not tps["email"]:
        fps = scrape_fastpeoplesearch(name, city, state)
        time.sleep(SCRAPE_DELAY_SECONDS)
        source_data = fps
    else:
        source_data = tps

    if not existing_phone and source_data["phone"]:
        lead["phone"] = source_data["phone"]
    if not existing_email and source_data["email"]:
        lead["email"] = source_data["email"]

    lead["enrichment_source"] = source_data["source"]
    lead["relatives"] = source_data.get("relatives", [])

    found = []
    if lead.get("phone"):
        found.append("phone")
    if lead.get("email"):
        found.append("email")
    log.info("Enriched %s: found %s via %s", name, found or "nothing", source_data["source"])

    return lead


def enrich_batch(leads: list[dict]) -> list[dict]:
    """Enrich a batch of leads. Returns the same list with enrichment data added."""
    log.info("Enriching batch of %d leads", len(leads))
    enriched = []
    for i, lead in enumerate(leads):
        log.info("Enriching %d/%d: %s", i + 1, len(leads), lead.get("full_name"))
        enriched.append(enrich_lead(lead))
    found_email = sum(1 for l in enriched if l.get("email"))
    found_phone = sum(1 for l in enriched if l.get("phone"))
    log.info("Batch enrichment complete. Emails found: %d/%d, Phones: %d/%d",
             found_email, len(enriched), found_phone, len(enriched))
    return enriched


if __name__ == "__main__":
    test_lead = {
        "full_name": "John Smith",
        "first_name": "John",
        "last_name": "Smith",
        "city": "Miami",
        "state": "FL",
        "zip_code": "33101",
    }
    result = enrich_lead(test_lead)
    print(json.dumps(result, indent=2))

"""Stage 1: Parse voter registration files and filter by demographics."""
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    DAILY_LEAD_LIMIT, MAX_AGE, MIN_AGE, OUTPUT_PATH,
    TARGET_CITIES, TARGET_STATE, TARGET_ZIPS, VOTER_FILE_PATH,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

FLORIDA_COLUMNS = [
    "county_code", "voter_id", "name_last", "name_first", "name_middle",
    "name_suffix", "suppress_address", "residence_address_line_1",
    "residence_address_line_2", "residence_city", "residence_state",
    "residence_zipcode", "mailing_address_line_1", "mailing_address_line_2",
    "mailing_address_line_3", "mailing_city", "mailing_state",
    "mailing_zipcode", "mailing_country", "gender", "race", "birth_date",
    "registration_date", "party_affiliation", "precinct", "precinct_group",
    "precinct_split", "precinct_suffix", "voter_status", "congressional_district",
    "house_district", "senate_district", "county_commission_district",
    "school_board_district", "daytime_area_code", "daytime_phone_number",
    "daytime_phone_extension", "email_address",
]

STATE_CONFIGS = {
    "FL": {
        "delimiter": "\t",
        "columns": FLORIDA_COLUMNS,
        "name_first": "name_first",
        "name_last": "name_last",
        "city": "residence_city",
        "state": "residence_state",
        "zip": "residence_zipcode",
        "dob": "birth_date",
        "gender": "gender",
        "race": "race",
        "party": "party_affiliation",
        "address": "residence_address_line_1",
        "phone_area": "daytime_area_code",
        "phone_number": "daytime_phone_number",
        "email": "email_address",
        "dob_format": "%m/%d/%Y",
    },
    "NC": {
        "delimiter": "\t",
        "columns": None,
        "name_first": "first_name",
        "name_last": "last_name",
        "city": "res_city_desc",
        "state": "state_cd",
        "zip": "zip_code",
        "dob": "birth_age",
        "gender": "gender_code",
        "race": "race_code",
        "party": "party_cd",
        "address": "res_street_address",
        "phone_area": None,
        "phone_number": "full_phone_number",
        "email": None,
        "dob_format": None,
    },
}


def calculate_age(birth_date_str: str, fmt: str) -> int | None:
    try:
        born = datetime.strptime(birth_date_str.strip(), fmt).date()
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except (ValueError, AttributeError):
        return None


def parse_voter_file(state: str = None, cities: list = None, zips: list = None,
                     min_age: int = None, max_age: int = None, limit: int = None) -> list[dict]:
    state = state or TARGET_STATE
    cities = cities or TARGET_CITIES
    zips = zips or TARGET_ZIPS
    min_age = min_age or MIN_AGE
    max_age = max_age or MAX_AGE
    limit = limit or DAILY_LEAD_LIMIT

    cfg = STATE_CONFIGS.get(state)
    if not cfg:
        log.error("No config for state: %s. Supported: %s", state, list(STATE_CONFIGS.keys()))
        return []

    voter_dir = Path(VOTER_FILE_PATH)
    csv_files = list(voter_dir.glob(f"{state}*.*")) + list(voter_dir.glob(f"{state.lower()}*.*"))
    if not csv_files:
        log.error("No voter files found in %s for state %s", voter_dir, state)
        return []

    file_path = csv_files[0]
    log.info("Reading voter file: %s", file_path)

    kwargs = {"sep": cfg["delimiter"], "dtype": str, "on_bad_lines": "skip", "low_memory": False}
    if cfg["columns"]:
        kwargs["names"] = cfg["columns"]
        kwargs["header"] = None
    df = pd.read_csv(file_path, **kwargs)
    log.info("Loaded %d raw records", len(df))

    city_col = cfg["city"]
    zip_col = cfg["zip"]

    cities_upper = [c.strip().upper() for c in cities if c.strip()]
    if cities_upper:
        df = df[df[city_col].str.upper().str.strip().isin(cities_upper)]
        log.info("After city filter (%s): %d records", cities_upper, len(df))

    if zips:
        df = df[df[zip_col].str[:5].isin(zips)]
        log.info("After zip filter: %d records", len(df))

    if cfg["dob_format"]:
        df["_age"] = df[cfg["dob"]].apply(lambda x: calculate_age(str(x), cfg["dob_format"]))
        df = df[df["_age"].notna()]
        df["_age"] = df["_age"].astype(int)
        df = df[(df["_age"] >= min_age) & (df["_age"] <= max_age)]
        log.info("After age filter (%d-%d): %d records", min_age, max_age, len(df))

    df = df.sample(frac=1, random_state=42).head(limit)
    log.info("Sampled %d leads (limit=%d)", len(df), limit)

    leads = []
    for _, row in df.iterrows():
        first = str(row.get(cfg["name_first"], "")).strip().title()
        last = str(row.get(cfg["name_last"], "")).strip().title()

        phone = ""
        if cfg.get("phone_area") and pd.notna(row.get(cfg["phone_area"])):
            area = str(row[cfg["phone_area"]]).strip()
            num = str(row.get(cfg["phone_number"], "")).strip()
            if area and num and len(num) >= 7:
                phone = f"+1{area}{num}"
        elif cfg.get("phone_number") and pd.notna(row.get(cfg["phone_number"])):
            raw = str(row[cfg["phone_number"]]).strip().replace("-", "").replace(" ", "")
            if len(raw) == 10:
                phone = f"+1{raw}"

        email = ""
        if cfg.get("email") and pd.notna(row.get(cfg["email"])):
            email = str(row[cfg["email"]]).strip().lower()

        lead = {
            "full_name": f"{first} {last}",
            "first_name": first,
            "last_name": last,
            "age": int(row["_age"]) if "_age" in row and pd.notna(row["_age"]) else None,
            "city": str(row.get(city_col, "")).strip().title(),
            "state": state,
            "zip_code": str(row.get(zip_col, ""))[:5],
            "address": str(row.get(cfg["address"], "")).strip(),
            "gender": str(row.get(cfg["gender"], "")).strip(),
            "race_ethnicity": str(row.get(cfg["race"], "")).strip(),
            "party_affiliation": str(row.get(cfg["party"], "")).strip(),
            "phone": phone,
            "email": email,
            "marital_status": "Unknown",
            "veteran_status": "Unknown",
            "homeowner": "Unknown",
            "date_sourced": date.today().isoformat(),
            "source": f"voter_file_{state}",
        }
        leads.append(lead)

    log.info("Parsed %d leads", len(leads))
    return leads


def save_leads(leads: list[dict], filename: str = None) -> str:
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    if not filename:
        filename = f"raw_leads_{date.today().isoformat()}.json"
    path = os.path.join(OUTPUT_PATH, filename)
    with open(path, "w") as f:
        json.dump(leads, f, indent=2)
    log.info("Saved %d leads to %s", len(leads), path)
    return path


if __name__ == "__main__":
    leads = parse_voter_file()
    if leads:
        save_leads(leads)
        log.info("Sample lead: %s", json.dumps(leads[0], indent=2))
    else:
        log.warning("No leads found. Check voter file path and filter settings.")

SCORING_WEIGHTS = {
    "age_55_75": 25,
    "age_45_54_or_76_85": 15,
    "veteran_confirmed": 30,
    "veteran_zip_proxy": 10,
    "married": 20,
    "homeowner": 15,
    "recent_home_purchase": 20,
    "recent_marriage": 15,
    "has_email": 5,
    "has_phone": 5,
    "target_city_match": 10,
    "prior_insurance_signal": 30,
    "expressed_interest": 50,
}

TIER_THRESHOLDS = {
    "A": {"min_score": 80, "requires_interest": True},
    "B": {"min_score": 60, "requires_interest": False},
    "C": {"min_score": 30, "requires_interest": False},
    "D": {"min_score": 0, "requires_interest": False},
}

TIER_COLUMNS = {
    "A": [
        "full_name", "age", "city", "state", "zip_code", "marital_status",
        "veteran_status", "race_ethnicity", "homeowner", "email", "phone",
        "lead_score", "lead_tier", "interest_expressed", "interest_channel",
        "prior_insurance_signal", "outreach_channels_used", "outreach_dates",
        "date_sourced", "date_qualified", "address",
    ],
    "B": [
        "full_name", "age", "city", "state", "zip_code", "marital_status",
        "veteran_status", "race_ethnicity", "homeowner", "email", "phone",
        "lead_score", "lead_tier", "interest_expressed",
        "outreach_channels_used", "outreach_dates", "date_sourced", "address",
    ],
    "C": [
        "full_name", "age", "city", "state", "zip_code", "marital_status",
        "veteran_status", "email", "phone", "lead_score", "lead_tier",
        "date_sourced", "address",
    ],
    "D": [
        "full_name", "age", "city", "state", "zip_code", "date_sourced",
    ],
}

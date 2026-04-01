"""Stage 4: Send personalized cold email outreach via Gmail SMTP."""
import logging
import smtplib
import sys
import time
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import GMAIL_ACCOUNTS, LANDING_PAGE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

account_send_counts = {i: 0 for i in range(len(GMAIL_ACCOUNTS))}


def load_template(template_name: str) -> str:
    path = TEMPLATES_DIR / template_name
    if not path.exists():
        log.error("Template not found: %s", path)
        return ""
    return path.read_text()


def pick_template(lead: dict) -> str:
    vet = str(lead.get("veteran_status", "")).lower()
    age = lead.get("age", 0)
    if vet in ("confirmed", "yes", "likely"):
        return "email_veteran.html"
    if age and age >= 55:
        return "email_senior.html"
    return "email_general.html"


def personalize(template_html: str, lead: dict) -> str:
    age = lead.get("age", 0)
    if age and age >= 65:
        age_group = "over 65"
    elif age and age >= 55:
        age_group = "55+"
    else:
        age_group = ""

    vet = str(lead.get("veteran_status", "")).lower()
    veteran_flag = "veteran" if vet in ("confirmed", "yes", "likely") else ""

    t = Template(template_html)
    return t.safe_substitute(
        first_name=lead.get("first_name", "there"),
        city=lead.get("city", "your area"),
        state=lead.get("state", ""),
        age_group=age_group,
        veteran_flag=veteran_flag,
        landing_url=LANDING_PAGE_URL or "https://example.com",
    )


def get_next_account() -> tuple[int, dict] | None:
    for idx, acct in enumerate(GMAIL_ACCOUNTS):
        if not acct.get("email") or not acct.get("password"):
            continue
        limit = acct.get("daily_limit", 50)
        if account_send_counts.get(idx, 0) < limit:
            return idx, acct
    return None


def send_email(lead: dict, subject: str = None, template_name: str = None) -> dict:
    result = {
        "lead_name": lead.get("full_name"),
        "email_sent_to": lead.get("email"),
        "template_used": "",
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "error": "",
    }

    email_to = lead.get("email", "")
    if not email_to or "@" not in email_to:
        result["error"] = "No valid email address"
        log.warning("No email for %s, skipping", lead.get("full_name"))
        return result

    if not template_name:
        template_name = pick_template(lead)
    result["template_used"] = template_name

    template_html = load_template(template_name)
    if not template_html:
        result["error"] = f"Template not found: {template_name}"
        return result

    body = personalize(template_html, lead)

    acct_info = get_next_account()
    if not acct_info:
        result["error"] = "All Gmail accounts at daily limit"
        log.error("All sending accounts exhausted")
        return result

    idx, acct = acct_info
    if not subject:
        vet = str(lead.get("veteran_status", "")).lower()
        city = lead.get("city", "your area")
        if vet in ("confirmed", "yes", "likely"):
            subject = f"Veterans in {city}: life insurance options you may qualify for"
        else:
            subject = f"Affordable life insurance options in {city}"

    msg = MIMEMultipart("alternative")
    msg["From"] = acct["email"]
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(acct["smtp"], acct["port"], timeout=30) as server:
            server.starttls()
            server.login(acct["email"], acct["password"])
            server.sendmail(acct["email"], email_to, msg.as_string())
        account_send_counts[idx] = account_send_counts.get(idx, 0) + 1
        result["success"] = True
        log.info("Sent email to %s via %s (%d/%d today)",
                 email_to, acct["email"], account_send_counts[idx], acct.get("daily_limit", 50))
    except Exception as e:
        result["error"] = str(e)
        log.error("Failed to send to %s: %s", email_to, e)

    return result


def send_batch(leads: list[dict], delay: int = 5) -> list[dict]:
    log.info("Sending outreach to %d leads", len(leads))
    results = []
    for i, lead in enumerate(leads):
        if not lead.get("email"):
            log.info("Skipping %s — no email", lead.get("full_name"))
            continue
        result = send_email(lead)
        results.append(result)
        if i < len(leads) - 1:
            time.sleep(delay)
    sent = sum(1 for r in results if r["success"])
    log.info("Outreach complete. %d/%d sent successfully", sent, len(results))
    return results


if __name__ == "__main__":
    log.info("Outreach module loaded. Configure GMAIL_ACCOUNTS in settings to send.")
    log.info("Templates directory: %s", TEMPLATES_DIR)
    log.info("Available templates: %s", [f.name for f in TEMPLATES_DIR.glob("*.html")])

"""Stage 2b: Verify email deliverability via syntax, DNS MX, and SMTP checks."""
import logging
import re
import smtplib
import socket
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

try:
    import dns.resolver
    HAS_DNS = True
except ImportError:
    HAS_DNS = False
    log.warning("dnspython not installed. MX checks disabled. pip install dnspython")

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "yopmail.com", "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "dispostable.com", "trashmail.com",
}


def check_syntax(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip().lower()))


def check_mx(domain: str) -> bool:
    if not HAS_DNS:
        return True
    try:
        records = dns.resolver.resolve(domain, "MX")
        return len(records) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers, dns.resolver.Timeout):
        return False
    except Exception:
        return False


def check_smtp(email: str, mx_host: str, timeout: int = 10) -> bool:
    try:
        with smtplib.SMTP(mx_host, 25, timeout=timeout) as smtp:
            smtp.ehlo("verify.local")
            smtp.mail("verify@verify.local")
            code, _ = smtp.rcpt(email)
            return code == 250
    except (smtplib.SMTPException, socket.timeout, socket.error, OSError):
        return False


def get_mx_host(domain: str) -> str | None:
    if not HAS_DNS:
        return None
    try:
        records = dns.resolver.resolve(domain, "MX")
        best = sorted(records, key=lambda r: r.preference)
        return str(best[0].exchange).rstrip(".")
    except Exception:
        return None


def verify_email(email: str) -> dict:
    email = email.strip().lower()
    result = {
        "email": email,
        "valid_syntax": False,
        "is_disposable": False,
        "has_mx": False,
        "smtp_reachable": False,
        "score": 0,
    }

    if not check_syntax(email):
        log.info("Invalid syntax: %s", email)
        return result
    result["valid_syntax"] = True
    result["score"] += 30

    domain = email.split("@")[1]
    if domain in DISPOSABLE_DOMAINS:
        result["is_disposable"] = True
        log.info("Disposable domain: %s", email)
        return result

    if not check_mx(domain):
        log.info("No MX records: %s", email)
        return result
    result["has_mx"] = True
    result["score"] += 40

    mx_host = get_mx_host(domain)
    if mx_host:
        if check_smtp(email, mx_host):
            result["smtp_reachable"] = True
            result["score"] += 30
        else:
            result["score"] += 10

    log.info("Verified %s: score=%d (syntax=%s, mx=%s, smtp=%s)",
             email, result["score"], result["valid_syntax"],
             result["has_mx"], result["smtp_reachable"])
    return result


def verify_batch(emails: list[str]) -> list[dict]:
    results = []
    for email in emails:
        if email and "@" in email:
            results.append(verify_email(email))
    valid = sum(1 for r in results if r["score"] >= 70)
    log.info("Verified %d emails. %d scored 70+", len(results), valid)
    return results


if __name__ == "__main__":
    test_emails = ["test@gmail.com", "fake@nonexistentdomain12345.com", "bad-syntax"]
    for email in test_emails:
        result = verify_email(email)
        print(f"{email}: score={result['score']}")

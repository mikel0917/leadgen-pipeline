# LeadGen Pipeline 🏥

> Fully automated life insurance lead generation system — from raw voter file data to CRM-ready outreach.

## Overview

This pipeline processes millions of voter file records, enriches them with demographic and contact data, scores them against a custom model, and reaches out via 4 channels — all orchestrated automatically with zero manual intervention.

**Built for production.** Runs on a Dockerized Ubuntu VPS with persistent n8n workflows and a live monitoring dashboard.

---

## Architecture

```
Voter File (9M records)
        ↓
  [Parser + Importer]          ← Auto-detects any state's CSV format
        ↓
  [Enrichment Cascade]         ← Hunter.io → Snov.io → ThatsThem → Fallback
        ↓
  [Scoring Engine]             ← Age, veteran status, marital status, CDL, etc.
        ↓
  [Multi-Channel Outreach]     ← Email / SMS / RVM / AI Voice
        ↓
  [Intent Capture Landing Page]← Name, coverage goal, beneficiary, branch
        ↓
  [CRM Export (CSV)]           ← Tiered A/B/C/D leads ready for agents
```

---

## Features

- **State-agnostic voter file parser** — auto-detects column formats from any US state
- **Enrichment cascade** with 85% phone hit rate and 55% email hit rate via Scrape.do
- **Custom lead scoring model** — 12 weighted factors including age, veteran status, CDL holder, homeowner
- **4-channel outreach** — Email (Resend), SMS (Twilio), Ringless Voicemail (Slybroadcast), AI Voice (Bland.ai)
- **TCPA-compliant** rate limiting and calling hour guardrails built in
- **Real-time dashboard** with pipeline controls, live stats, and CSV export
- **Full n8n workflow** on a single canvas — visual, auditable, modifiable

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Backend | Python, Flask |
| Orchestration | n8n |
| Infrastructure | Docker, Ubuntu VPS, Nginx |
| Enrichment | Scrape.do, Hunter.io, Snov.io |
| Outreach | Twilio, Resend, Bland.ai, Slybroadcast |
| Dashboard | Flask + htmx + Tailwind CSS |
| Data | PostgreSQL, CSV |

---

## Key Scripts

```
parse_voter_file.py     → State-agnostic voter file parser
import_csv.py           → Bulk record importer with deduplication
enrich_lead.py          → Multi-source enrichment cascade
score_leads.py          → Custom scoring engine (A/B/C/D tiers)
send_outreach.py        → Email via Resend
send_sms.py             → SMS via Twilio
send_rvm.py             → Ringless voicemail via Slybroadcast
ai_caller.py            → AI voice calls via Bland.ai
track_interest.py       → Landing page intent capture
export_csv.py           → Tiered CRM export
rate_limiter.py         → TCPA-compliant rate controls
api/server.py           → Flask REST API
api/dashboard.py        → Monitoring dashboard
```

---

## Scoring Model

| Factor | Points |
|--------|--------|
| Age 55–75 | +25 |
| Veteran confirmed | +30 |
| CDL holder | +20 |
| Married | +20 |
| Homeowner | +15 |
| Age 45–54 or 76–85 | +15 |
| Target city | +10 |
| Has email | +5 |
| Has phone | +5 |
| Expressed interest | +50 |

**Tiers:** A (80+) · B (60–79) · C (30–59) · D (<30)

---

## Setup

```bash
git clone https://github.com/mikel0917/leadgen-pipeline
cd leadgen-pipeline
cp .env.example .env
# Fill in API keys
docker-compose up -d
```

Dashboard available at `http://localhost:5001/dashboard`
n8n available at `http://localhost:5678`

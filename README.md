# AccessGuard — ITGC User Access Review Automation for Banking

AccessGuard automates the **User Access Review (UAR)** that IT auditors perform during ITGC (IT General Controls) testing at banks. It reconciles HR employee data with user lists pulled from banking systems, flags access exceptions, rates their risk, and produces an audit-ready report (Excel + PDF).

> **Status:** In active development. Being built phase by phase — see [Build Progress](#build-progress) below.

---

## Table of Contents

- [Why this exists — ITGC background](#why-this-exists--itgc-background)
- [What AccessGuard does](#what-accessguard-does)
- [Checks → Risk mapping](#checks--risk-mapping)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Tech stack](#tech-stack)
- [Setup](#setup)
- [Screenshots](#screenshots)
- [Build progress](#build-progress)

---

## Why this exists — ITGC background

**ITGC (IT General Controls)** are the controls auditors test to determine whether they can rely on a bank's IT systems to produce accurate financial and operational data. One of the most common and highest-risk ITGC controls is the **User Access Review**: periodically confirming that only the right people have access to sensitive systems (core banking, loan origination, databases), at the right privilege level, for the right reasons.

During a UAR, an IT auditor typically:

1. Pulls the **HR master list** (who is employed, their department, and their status — active or terminated).
2. Pulls **user/account lists** from each in-scope system (core banking, loan system, database, etc.).
3. **Reconciles** the two: does every system account map to a real, active employee? Was access removed promptly when someone left? Does anyone hold conflicting privileges (Segregation of Duties)? Are there shared/generic logins that break individual accountability? Are there dormant accounts that should have been disabled?
4. **Rates each exception by risk** (e.g., a terminated employee with active access to move money is a High risk; a dormant read-only account is Low).
5. Writes up findings in **audit format** — Condition, Criteria, Risk/Impact, Recommendation — for the audit workpapers and management response.

Banks are required to perform this review because unrevoked or excessive access is one of the most frequently cited findings in SOX/ITGC and regulatory (RBI, OCC, FFIEC, etc.) audits — it directly enables fraud, unauthorized transactions, and data breaches. Doing this manually in Excel, for hundreds or thousands of employees across multiple systems, is slow and error-prone. **AccessGuard automates the reconciliation, risk-rating, and reporting**, so an auditor's time goes into judgment and follow-up rather than VLOOKUPs.

## What AccessGuard does

Given an HR employee export and CSV user lists from each in-scope banking system, AccessGuard:

- Reconciles HR status against system account status
- Runs a configurable library of exception checks (see table below)
- Assigns a risk rating to every finding
- Lets an auditor review, filter, and search findings in a dashboard
- Generates a professional, audit-ready **Excel workbook** and **PDF report**

## Checks → Risk mapping

| # | Check | What it detects | Risk rating |
|---|-------|------------------|--------------|
| 1 | Terminated users with active access | HR status = Terminated but the system account is still Active | **High** |
| 2 | Late revocation | Account was disabled more than 1 day after the termination date | **Medium** |
| 3 | Orphan accounts | System account has no matching HR employee record | **High** |
| 4 | Generic / shared accounts | Usernames matching shared-account patterns (e.g. `admin`, `test`, `temp`, `teller01`, `shared`) | **Medium** |
| 5 | Privileged access listing | All Admin/DBA accounts; flagged if the holder sits outside the IT department | **High** (outside IT) / **Informational** (inside IT) |
| 6 | Segregation of Duties (SoD) conflicts | An employee holds two roles that conflict per `sod_rules.json` (e.g. Loan Creator + Loan Approver), within or across systems | **High** |
| 7 | Dormant accounts | No login in 90+ days (configurable) | **Low** |

## Architecture

```
┌───────────────┐        ┌────────────────────────┐        ┌───────────────────┐
│   React UI    │  HTTP  │   FastAPI backend       │        │   PostgreSQL       │
│ (Tailwind CSS)│ ─────▶ │ - Upload & validation   │ ─────▶ │ - Employees        │
│               │ ◀───── │ - Review engine (Pandas)│ ◀───── │ - System accounts  │
│ Dashboard,    │  JSON  │ - Risk-rated findings   │        │ - Reviews/Findings │
│ findings table│        │ - JWT auth (Auditor/    │        └───────────────────┘
│ upload page   │        │   Viewer roles)         │
└───────────────┘        │ - Report generation     │
                          │   (openpyxl, ReportLab) │
                          └────────────────────────┘
```

All three services (frontend, backend, postgres) run together via Docker Compose.

## Project structure

```
AccessGuard/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routers: auth, uploads, reviews
│   │   ├── services/        # Upload validation/ingest, review execution and queries
│   │   ├── checks/          # One module per audit check, auto-registered via @register_check
│   │   ├── main.py          # FastAPI app entrypoint
│   │   ├── models.py        # SQLAlchemy models (users, datasets, reviews, findings)
│   │   ├── auth.py          # JWT + bcrypt, role-based dependencies
│   │   ├── config.py        # ReviewConfig: thresholds, privileged roles, generic patterns, SoD rules
│   │   ├── data_loading.py  # CSV reading, column validation, normalization
│   │   ├── review.py        # Runs all checks, assigns finding IDs, builds summaries
│   │   └── cli.py           # Command-line review runner
│   ├── tests/               # pytest suite: small fixtures with known exceptions per check
│   ├── scripts/
│   │   └── generate_dummy_data.py   # Faker-based synthetic data generator (Phase 1)
│   ├── data/                # Generated sample CSVs (HR + 3 system exports)
│   ├── config/
│   │   └── sod_rules.json   # Configurable Segregation-of-Duties rules
│   └── requirements.txt
├── frontend/                # React + Tailwind app — added in Phase 4
├── docker-compose.yml       # Postgres + backend (frontend added in Phase 4)
└── README.md
```

## Tech stack

- **Backend:** Python, FastAPI, Pandas, SQLAlchemy
- **Database:** PostgreSQL
- **Frontend:** React + Tailwind CSS
- **Reports:** openpyxl (Excel), ReportLab (PDF)
- **Auth:** JWT, with Auditor (run reviews, view) and Viewer (view only) roles
- **Deployment:** Docker Compose
- **Tests:** pytest

## Setup

### Run with Docker (backend + PostgreSQL)

```bash
docker compose up -d --build
```

The API is at http://localhost:8000, with interactive docs at http://localhost:8000/docs. Two demo users are created on startup:

| Username | Password | Role | Can |
|----------|----------|------|-----|
| `auditor` | `Auditor@123` | Auditor | Upload files, run reviews, view everything |
| `viewer` | `Viewer@123` | Viewer | View reviews, findings, and summaries only |

Override these, plus `JWT_SECRET` and `POSTGRES_PASSWORD`, with environment variables for anything beyond a local demo.

### Run locally (without Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/generate_dummy_data.py
```

This produces `hr_employees.csv`, `core_banking_users.csv`, `loan_system_users.csv`, and `database_users.csv` in `backend/data/`, with realistic, deliberately-planted exceptions (15–25 per check) for every check above. Output is seeded, so every run produces identical data.

System CSV columns: `user_id, employee_id, username, role, account_status, created_date, last_login_date, status_last_updated`. `status_last_updated` records when the account status last changed, and is what the late-revocation check uses to measure how long after termination an account was disabled.

Start the API locally. Without `DATABASE_URL` it uses a SQLite file, `backend/accessguard.db`:

```bash
uvicorn app.main:app --reload
```

Or run all audit checks straight from the terminal, and run the test suite:

```bash
python -m app.cli --as-of 2026-09-27   # prints summary; writes output/findings.csv
pytest
```

`--as-of` is the date the data was extracted, which dormancy is measured against. The sample data was generated as of 2026-09-27.

### Adding a new check

Create a module in `backend/app/checks/`, decorate a function `(ReviewContext) -> list[Finding]` with `@register_check(...)`, and supply its criteria, impact, and recommendation text (used in the audit report). Then import the module in `app/checks/__init__.py`. The runner, summary, API, and reports pick it up automatically.

## API

All endpoints except `/auth/login` and `/health` require `Authorization: Bearer <token>`.

| Method | Endpoint | Role | Purpose |
|--------|----------|------|---------|
| POST | `/auth/login` | - | Form login (`username`, `password`), returns a JWT |
| GET | `/auth/me` | any | Current user |
| POST | `/upload` | Auditor | Multipart: `hr_file` (required) plus at least one of `core_banking_file`, `loan_system_file`, `database_file` |
| GET | `/datasets` | any | Uploaded datasets, newest first |
| GET | `/checks` | any | Check catalogue: code, name, criteria, impact, recommendation |
| POST | `/reviews/run` | Auditor | JSON `{"dataset_id"?, "as_of_date"?}`. Defaults to the latest dataset and today |
| GET | `/reviews` / `/reviews/{id}` | any | Review metadata |
| GET | `/reviews/{id}/findings` | any | Filters: `system`, `check` (code), `risk_rating`, `search`; paging: `limit`, `offset` |
| GET | `/reviews/{id}/summary` | any | Counts by risk, check, and system |
| GET | `/reviews/{id}/report/excel`, `/report/pdf` | any | Added in Phase 5 |

Uploads are validated before anything is stored. A rejected upload returns `422` and lists every problem in every file at once, with file names and row numbers, for example:

```json
{"detail": {"message": "Upload rejected: 2 problem(s) found.", "errors": [
  {"file": "hr_employees.csv", "error": "'status' must be Active or Terminated at row 4."},
  {"file": "loan_system_users.csv", "error": "Missing required column(s): role. Expected columns: ..."}
]}}
```

Checks: `.csv` extension, UTF-8 encoding, 10 MB limit, required columns, at least one data row, no blank key fields, unique `employee_id`/`user_id`, `YYYY-MM-DD` dates, HR status of `Active` or `Terminated`, and a termination date for every terminated employee.

## Screenshots

_Screenshots of the dashboard, findings table, and generated reports will be added here once the frontend is built._

## Build progress

- [x] Phase 1 — Dummy data generator
- [x] Phase 2 — Audit checks (core logic) + unit tests
- [x] Phase 3 — Backend API (FastAPI + JWT auth + PostgreSQL)
- [ ] Phase 4 — Frontend (React dashboard)
- [ ] Phase 5 — Audit report generation (Excel + PDF)
- [ ] Phase 6 — Full test suite, polish, Docker Compose

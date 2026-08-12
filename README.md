# GrievancePath — Smart Grievance Routing System

Built for **Smart India Hackathon**. Citizens describe their problem in plain
language; the system **analyses it and automatically routes the grievance to the
correct government department** — the citizen never has to know which department
handles what.

![Stack](https://img.shields.io/badge/backend-FastAPI-teal) ![DB](https://img.shields.io/badge/db-SQLite-blue) ![ML](https://img.shields.io/badge/routing-keyword%2BML-purple)

## The problem we solve

Today a citizen must know that a pothole is "PWD" but a broken street light is
"Municipal Corporation", that water supply issues are a separate department, and
so on. Our system removes that burden:

- Citizen types a complaint like _"The street lights on my lane haven't worked for a week"_
- The **routing engine** reads the text and sends it to **Municipal Corporation**
  with a confidence score and the matched keywords shown to the user.
- The department signs in and resolves it; the citizen gets SMS/email-style updates.
- An admin panel + analytics page gives the full picture for the judges.

## Pages

| Route | Page | Purpose |
|---|---|---|
| `/` | Citizen portal | Lodge complaint (with **live department prediction** as you type) + track status by ID |
| `/department` | Department dashboard | Sign in as any department, see assigned complaints, update status/priority, leave notes |
| `/admin` | Admin panel | Overview stats, manage/reassign any complaint, notification log |
| `/analytics` | Analytics | Charts: by department, status donut, 14-day trend, priority mix, routing method |
| `/docs` | Swagger | Auto-generated API docs |

Demo logins: admin password `admin123` · any department password `dept123`
(change in `.env`).

## How the auto-routing engine works

1. **Keyword classifier** — 15 departments, each with weighted positive/negative
   keyword lists (e.g. `power cut +5`, `street light −1` for the Electricity Board).
   Fully offline, deterministic and explainable.
2. **ML layer** — a TF-IDF + Multinomial Naive-Bayes model (scikit-learn) is
   trained at startup from the keyword tables, so *novel* phrasings still land in
   the right department. Runs offline.
3. **Optional LLM** — set `LLM_API_KEY` in `.env` and the engine cross-checks its
   decision with an LLM (`ROUTER_DEFAULT=hybrid`), falling back gracefully if the
   call fails.

Every route stores its method, confidence and matched keywords on the complaint
(`routing_method`, `department_confidence`, `matched_keywords`) so the whole
decision is auditable.

## Databases (SQLite, in `data/grievances.db`)

| Table | Purpose |
|---|---|
| `departments` | 15 departments (code, name, contact, colour) |
| `keywords` | keyword → department routing weights |
| `complaints` | grievances + routed department, confidence, status, priority |
| `status_history` | full audit trail of every status change |
| `notifications` | SMS/email log (simulated out-of-the-box) |
| `llm_feedback` | LLM vs classifier agreement logging |

Schema is auto-created and seeded on first run with **20 realistic demo
complaints** so the analytics pages are instantly impressive.

## Run it

```powershell
# from this folder (grievance-system)
..\.venv\Scripts\python.exe -m pip install -r requirements.txt   # once
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Then open:
- Citizen portal: http://localhost:8000/
- Analytics: http://localhost:8000/analytics
- Department dashboard: http://localhost:8000/department (pick any department, password `dept123`)
- Admin: http://localhost:8000/admin (password `admin123`)
- API docs: http://localhost:8000/docs

## Project layout

```
grievance-system/
├── app/
│   ├── main.py                # FastAPI app + all routes
│   ├── config.py              # settings from .env
│   ├── database.py            # SQLite schema + connection helpers
│   ├── schemas.py             # request/response models
│   ├── routing/
│   │   ├── classifier.py      # keyword scorer + TF-IDF/ML classifier
│   │   ├── llm.py             # optional OpenAI-compatible LLM router
│   │   └── service.py         # orchestrator (classifier + ML + LLM)
│   ├── services/
│   │   ├── complaint.py       # create/track/update/notify
│   │   ├── analytics.py       # analytics queries
│   │   └── seed.py            # departments, keywords, demo complaints
│   └── static/                # citizen portal, dept/admin/analytics pages
├── data/                      # grievances.db (auto-created)
├── requirements.txt
└── .env.example               # copy to .env and tweak
```

## Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/analyze` | Preview the routing decision for text (used by live analysis) |
| POST | `/api/complaints` | Submit a complaint → auto-routed |
| GET  | `/api/complaints/track?tracking_id=GRV-2026-0001` | Track status + history |
| POST | `/api/login` | `role=admin` or `role=department&code=MCD` |
| GET  | `/api/dept/complaints` | A department's assigned complaints |
| POST | `/api/dept/complaints/{id}/update` | Update status/priority with a note |
| GET  | `/api/admin/overview` · `/api/admin/complaints` · `/api/admin/notifications` | Admin data |
| GET  | `/api/analytics/*` | Departments, status, priority, trend, routing |

## Making it production-ready

- **Real email/SMS**: fill the SMTP block in `.env` (alerts already work simulated).
- **LLM routing**: set `LLM_API_KEY` (works with any OpenAI-compatible API).
- **Auth**: replace the demo password + in-memory sessions with real accounts
  (e.g. FastAPI users + JWT).
- **DB**: `data/grievances.db` is SQLite; swap to PostgreSQL by changing
  `database.py` if you expect heavy load.

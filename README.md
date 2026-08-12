# GrievancePath — Smart Grievance Routing System

> **Source code:** https://github.com/Hufaidkhan369/grievance-path
> After you deploy (below), your public URL will be `https://grievance-path.onrender.com`.

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
| `/` | Citizen portal | Lodge complaint (with **live department prediction** as you type), citizen accounts, manual-mode routing, track with status stepper + SLA + rate-it feedback |
| `/department` | Department dashboard | Sign in as any department, per-department queue with SLA/overdue flags, update status/priority, leave notes |
| `/admin` | Admin panel | Everything in one place: complaints, users, feedback, notifications, retrain the model, manually route any complaint |
| `/analytics` | Analytics | Charts: by department, status donut, 14-day trend, priority mix, routing method, users, ratings |
| `/docs` | Swagger | Auto-generated API docs |

Demo logins: admin password `admin123` · any department password `dept123`
(change in `.env`).

## How the auto-routing engine works

1. **Keyword classifier** — 15 departments, each with weighted positive/negative
   keyword lists (e.g. `power cut +5`, `street light −1` for the Electricity Board).
   Fully offline, deterministic and explainable.
2. **Trained ML model** — a TF-IDF + Multinomial Naive-Bayes model is trained
   (`train_model.py`) on 1200+ generated samples from the keyword tables and real
   seeded complaints, so *novel* phrasings still land in the right department.
   Runs offline; retrain any time from the admin panel.
3. **Optional LLM** — set `LLM_API_KEY` in `.env` and the engine cross-checks its
   decision with an LLM (`ROUTER_DEFAULT=hybrid`), falling back gracefully if the
   call fails.
4. **Manual mode** — a citizen can always override and pick the department
   themselves; admins can force-route any complaint (`routing_method = manual`).

Every route stores its method, confidence and matched keywords on the complaint
(`routing_method`, `department_confidence`, `matched_keywords`) so the whole
decision is auditable.

## Databases (SQLite, in `data/grievances.db`)

| Table | Purpose |
|---|---|
| `departments` | 15 departments (code, name, contact, colour) |
| `keywords` | keyword → department routing weights |
| `users` | citizen accounts (register/sign in, linked to complaints) |
| `complaints` | grievances + routed department, confidence, status, priority, SLA |
| `department_complaints` | **per-department queue** — each department's own list with SLA due date |
| `status_history` | full audit trail of every status change |
| `notifications` | SMS/email log (simulated out-of-the-box) |
| `feedback` | citizen ratings (★ 1–5) + comments per complaint |
| `llm_feedback` | LLM vs classifier agreement logging |

Schema is auto-created and seeded on first run with **20 realistic demo
complaints**, sample users and feedback so every page is instantly impressive.

## Deploy to the web (public URL) — 2 minutes

The repo is ready at **https://github.com/Hufaidkhan369/grievance-path** with a
Render blueprint (`render.yaml`). To get a permanent public URL on the free tier:

1. Create a free account at **https://render.com** (sign in with GitHub).
2. In the Render dashboard click **New → Blueprint**.
3. Choose the `grievance-path` repository.
4. Click **Apply** — Render reads `render.yaml` and builds/deploys automatically.
5. Your public URL will be **https://grievance-path.onrender.com** (shown in the
   dashboard once deployed). It's live worldwide within ~2 minutes.

> Note: the free tier uses an ephemeral disk, so the SQLite demo data resets on
> redeploys. Perfect for demos; switch `database.py` to PostgreSQL for permanent data.

## Run it locally

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

Optional: re-train the routing model:
```powershell
..\.venv\Scripts\python.exe train_model.py
```

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
│   │   ├── complaint.py       # create/track/update/notify + per-dept queue
│   │   ├── users.py           # citizen register/login
│   │   ├── analytics.py       # analytics queries
│   │   └── seed.py            # departments, keywords, demo data
│   └── static/                # citizen portal, dept/admin/analytics pages
├── models/routing_model.joblib  # trained TF-IDF + Naive-Bayes model
├── data/                      # grievances.db (auto-created)
├── train_model.py             # trains & saves the routing model
├── render.yaml                # Render.com blueprint (public deploy)
├── requirements.txt
└── .env.example               # copy to .env and tweak
```

## Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/analyze` | Preview the routing decision for text (used by live analysis) |
| POST | `/api/complaints` | Submit a complaint → auto-routed (or manual `manual_department_code`) |
| GET  | `/api/complaints/track?tracking_id=GRV-2026-0001` | Track status + history + SLA |
| POST | `/api/complaints/{id}/feedback` | Citizen rating + comment |
| POST | `/api/auth/register` · `/api/auth/login` | Citizen accounts |
| POST | `/api/login` | `role=admin` or `role=department&code=MCD` |
| GET  | `/api/dept/complaints` · `/api/dept/queue-stats` | A department's own queue + SLA stats |
| POST | `/api/dept/complaints/{id}/update` | Update status/priority with a note |
| GET  | `/api/admin/overview` · `/users` · `/feedback` · `/notifications` | Admin sees everything |
| POST | `/api/admin/train` · `/api/admin/complaints/{id}/manual-route` | Retrain model / force route |
| GET  | `/api/analytics/*` | Departments, status, priority, trend, routing |

## Making it production-ready

- **Real email/SMS**: fill the SMTP block in `.env` (alerts already work simulated).
- **LLM routing**: set `LLM_API_KEY` (works with any OpenAI-compatible API).
- **Auth**: replace the demo password + in-memory sessions with real accounts
  (e.g. FastAPI users + JWT).
- **DB**: `data/grievances.db` is SQLite; swap to PostgreSQL by changing
  `database.py` if you expect heavy load.

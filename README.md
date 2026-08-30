# Smart Expense Tracker 💸

A full-stack, AI-powered personal finance app where messy bank/UPI transaction text becomes structured, categorized financial data — combining an LLM categorization pipeline, a relational database with a full audit trail, and per-user authentication into one working system.

---

## What it does

- Upload a bank/UPI statement CSV and have every transaction parsed into structured records
- Add transactions manually through the dashboard, no CSV required
- Let an LLM automatically categorize each transaction and extract a clean merchant name from raw, inconsistent descriptions (*"SWIGGY*ORD 88213 BLR"* → merchant: **Swiggy**, category: **Food**)
- Correct a wrong AI category with one action — the correction (original → corrected) is permanently logged, not just overwritten
- View spend broken down by category as proportional ledger-style bars
- View monthly income v/s spend totals
- See top merchants by total spend
- Register/login with a personal account — every transaction, upload, and categorization run is scoped to that account only
- Browse transaction history with pagination, built to scale beyond a handful of rows

---

## What makes it different

Most expense trackers require you to manually tag every transaction, or rely on brittle keyword rules that break the moment a bank changes its statement format.

| Feature | Traditional approach | Smart Expense Tracker |
|---|---|---|
| **Categorization** | Manual tagging or fixed keyword rules | LLM reads the raw description and classifies it, no rules to maintain |
| **Merchant identification** | Not extracted — raw text shown as-is | LLM extracts a clean merchant name in the same API call |
| **Correcting mistakes** | Overwrite and lose the original value | Every correction is logged (original → corrected) for a real audit trail |
| **AI failures** | Often crash the whole batch | Failed categorizations fall back safely to "Other" and processing continues |
| **Data ownership** | Often single-user or unscoped | JWT auth scopes every query to the logged-in user, verified via testing |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | MySQL |
| AI / LLM | Groq API (`openai/gpt-oss-120b`) |
| Auth | JWT (`python-jose`), `bcrypt` password hashing |
| Frontend | React (Vite) |
| Styling | Custom CSS — dark ledger theme, Space Grotesk + IBM Plex Mono |

---

## How it works

```
User uploads a CSV, or adds a transaction manually
                      ↓
FastAPI parses/validates the input (Pydantic: amount > 0, valid date, valid txn_type)
                      ↓
Transaction stored in MySQL — category_id NULL, category_source = "uncategorized"
                      ↓
User triggers "Categorize Pending"
                      ↓
For each uncategorized transaction:
raw description → Groq LLM prompt (structured JSON output)
                      ↓
LLM returns { "merchant_name": ..., "category": ... }
                      ↓
If the API call fails → fallback to category "Other", logged, processing continues
If the returned category isn't in the valid list → fallback to "Other"
                      ↓
transaction updated: category_id set, category_source = "ai"
                      ↓
[Optional] User manually corrects a wrong category
                      ↓
original category logged to correction_log
                      ↓
transaction updated: category_source = "manual"
                      ↓
React dashboard fetches /transactions (paginated) and /summary/* endpoints
                      ↓
Category bars, monthly totals, and top merchants render from live SQL aggregation
```

---

## Project Structure

```
Expense-Tracker/
├── backend/
│   ├── main.py                    # FastAPI app: all endpoints (auth, transactions, upload, categorize, summaries)
│   ├── auth.py                    # Password hashing, JWT creation/verification, user lookup
│   ├── ingest.py                  # DB connection config, CSV/row ingestion logic
│   ├── categorize.py              # Groq prompt, categorization loop, manual correction logic
│   ├── schema.sql                 # Full MySQL schema (categories, transactions, correction_log, users)
│   ├── data/
│   │   └── mock_transactions.csv
└── frontend/
│   └── src/
│   │   ├── App.jsx                # Dashboard, login/register screen, all fetch logic
│   │   └── App.css                # Dark ledger theme, proportional category bars, badges
```

---

## Database Schema

4 core tables:

```
users — username + bcrypt password hash
categories — fixed spending categories (Food, Rent, Transport, Income, etc.)
transactions — date, raw description, merchant name, amount, type, category, category_source (ai/manual/uncategorized), linked to a user
correction_log — audit trail: transaction_id, original_category_id, corrected_category_id
```

---

## Setup and Installation

### Pre-requisites
- Python 3.11+
- Node.js 18+
- MySQL 8.0
- Groq API key ([console.groq.com](https://console.groq.com))

### 1. Clone the repository

```bash
git clone https://github.com/krishgoel20/Smart-Expense-Tracker.git
cd Smart-Expense-Tracker
```

### 2. Set up the backend

```bash
pip install fastapi uvicorn mysql-connector-python python-dotenv groq bcrypt python-jose[cryptography] python-multipart
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=expense_tracker

GROQ_API_KEY=your_groq_api_key
JWT_SECRET=your_long_random_secret
```

### 4. Run the backend

Run the database schema:

```bash
mysql -u root -p < schema.sql
```

Start the backend:

```bash
uvicorn main:app --reload
```

API runs at `http://127.0.0.1:8000` — interactive docs at `/docs`.

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`.

### 7. Create an account

Register a new user directly from the app's login screen — no seed credentials required.

---

## Features

### AI Features
- **AI Categorization** — a single Groq API call reads the raw transaction description and returns structured JSON with both a category and a clean merchant name
- **Graceful degradation** — if the Groq API call fails (rate limit, outage, invalid key), the transaction falls back to category "Other" instead of crashing the whole batch, and the failure is logged
- **Category validation** — if the LLM ever returns a category outside the approved list, it's caught and defaulted to "Other" rather than corrupting the database

### Expense Tracking Features
- **CSV upload** — parse a full bank/UPI statement in one request
- **Manual transaction entry** — add a single transaction directly from the dashboard
- **Manual correction with audit trail** — override any AI-assigned category; the original and corrected values are both permanently logged
- **Pagination** — transactions load 10 at a time with Previous/Next controls, built to scale past a handful of rows
- **Analytics** — spend-by-category (rendered as proportional bars), monthly income vs. spend, and top-5 merchants by spend, all computed via SQL aggregation

### Auth & Access
- **JWT authentication** — register/login with bcrypt-hashed passwords, 24-hour token expiry
- **Per-user data isolation** — every transaction, upload, and categorization run is scoped to `user_id`; verified directly by testing that a second account sees zero of the first account's data
- **Persistent login** — token stored in `localStorage`, survives a page refresh

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a new account, returns a JWT |
| POST | `/auth/login` | Log in, returns a JWT |

### Transactions
| Method | Endpoint | Description |
|---|---|---|
| GET | `/transactions` | List transactions (paginated, auth required) |
| POST | `/transactions` | Manually add a transaction |
| POST | `/upload` | Upload a CSV of transactions |
| POST | `/categorize` | Run AI categorization on pending transactions |
| PUT | `/transactions/{id}/category` | Manually correct a transaction's category |

### Analytics
| Method | Endpoint | Description |
|---|---|---|
| GET | `/summary/by-category` | Total spend per category |
| GET | `/summary/monthly` | Monthly spend vs. income |
| GET | `/summary/top-merchants` | Top 5 merchants by spend |

---

## Key Concepts Demonstrated

- **Structured LLM Output** — the categorization prompt requests strict JSON (`response_format={"type": "json_object"}`) so both category and merchant name are extracted in a single API call, parsed and validated before being written to the database.
- **Defensive handling of unreliable AI output** — every LLM call is wrapped so a failed request, a malformed response, or a category outside the approved list all degrade safely to a known fallback ("Other") instead of crashing the batch or corrupting data.
- **Audit-logged corrections** — `correction_log` captures the original AI-assigned category before it's overwritten, so every manual fix is traceable rather than silently lost.
- **JWT Authentication with verified data isolation** — every protected endpoint depends on a shared `get_current_user` function; every query touching `transactions` filters by `user_id`. This was explicitly tested by confirming a second registered account returns zero transactions belonging to the first.
- **Password security** — passwords are hashed with `bcrypt` before storage; plaintext passwords are never persisted or logged.
- **Environment-based configuration** — database credentials, the Groq API key, and the JWT signing secret are all loaded from a `.env` file excluded from version control via `.gitignore`, never hardcoded in source.
- **Pagination via SQL `LIMIT`/`OFFSET`** — the transactions endpoint returns a fixed page size plus total-page metadata, avoiding loading the entire table into memory as data grows.

---

## Limitations

- **No cloud deployment yet** — the app currently runs locally only; both backend and frontend require local servers to be running.
- **Fixed category list** — categories are seeded once and not yet user-editable from the UI (adding a category currently requires a direct database insert).
- **No CSV upload UI validation** — a malformed CSV (wrong column names, bad date formats) will currently fail ungracefully rather than showing a clear error to the user.
- **Single currency** — all amounts are treated as a single implicit currency (₹); no multi-currency support.
- **LLM categorization is non-deterministic across providers** — the categorization prompt is tuned for the currently configured Groq model; switching models may shift category-boundary decisions on ambiguous transactions.
- **No password reset flow** — unlike a production auth system, there's currently no "forgot password" email flow; a lost password requires a direct database update.

---

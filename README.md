# Smart Expense Tracker

A full-stack expense tracking app that uses an LLM to automatically categorize transactions and extract merchant names from messy bank/UPI statement descriptions — combining a relational database, a REST API, and an AI pipeline into one working system.

## Features

- **CSV ingestion** — upload a bank/UPI statement CSV and parse it into structured transaction records
- **AI categorization** — Groq-hosted LLM (`openai/gpt-oss-120b`) classifies each transaction into a category and extracts a clean merchant name, using structured JSON output
- **Manual correction with audit trail** — override an AI-assigned category, with every correction logged (original → corrected) in a dedicated table
- **Authentication** — JWT-based login/register with bcrypt password hashing; every transaction is scoped to its owner
- **Analytics** — spend-by-category, monthly income vs. spend, and top-merchant summaries, computed via SQL aggregation
- **Paginated, styled dashboard** — a React frontend with a dark ledger-style UI, proportional category bar charts, and live data refresh after every action

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** MySQL
- **AI:** Groq API (LLM-based categorization + merchant extraction)
- **Frontend:** React (Vite)
- **Auth:** JWT (python-jose), bcrypt password hashing

## Architecture

CSV / manual entry → FastAPI → MySQL (transactions, categories, correction_log, users)
↓
Groq LLM categorization
↓
React dashboard (paginated, per-user)


## Database Schema

- **`categories`** — fixed list of spending categories (Food, Rent, Transport, etc.)
- **`transactions`** — core table: date, raw description, merchant name, amount, type, category, category source (ai/manual/uncategorized), linked to a user
- **`correction_log`** — audit trail of every manual category correction (original category → corrected category)
- **`users`** — username + bcrypt password hash

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create a new account |
| POST | `/auth/login` | Log in, receive a JWT |
| GET | `/transactions` | List transactions (paginated, auth required) |
| POST | `/transactions` | Manually add a transaction |
| POST | `/upload` | Upload a CSV of transactions |
| POST | `/categorize` | Run AI categorization on pending transactions |
| PUT | `/transactions/{id}/category` | Manually correct a transaction's category |
| GET | `/summary/by-category` | Total spend per category |
| GET | `/summary/monthly` | Monthly spend vs. income |
| GET | `/summary/top-merchants` | Top merchants by spend |

## Setup

### Backend
```bash
pip install -r requirements.txt
# create a .env file with:
#   DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
#   GROQ_API_KEY
#   JWT_SECRET
uvicorn main:app --reload
```

### Database
Run `schema.sql` against a MySQL instance to create the required tables.

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Notable Design Decisions

- **Structured JSON output from the LLM** (rather than plain text parsing) to extract both category and merchant name in a single API call
- **Graceful degradation** — if the Groq API call fails, the transaction falls back to category "Other" instead of crashing the whole batch
- **Correction audit trail** — every manual override is logged with both the original and corrected category, not just overwritten
- **Per-user data isolation** — every query is scoped by `user_id`, verified via testing that one account cannot see another's transactions

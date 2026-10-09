# BookLeaf Author Support Portal

An AI-powered support portal for BookLeaf Publishing. Authors can view their books, sales, royalties, and raise support tickets. Admins manage tickets, review AI-generated replies, and respond to authors.

## 1. Features

**Author Portal**
- View books, ISBNs, sales, and royalty details.
- Create support tickets with optional attachments.
- View conversations and receive new replies.
- Reply to tickets and track their status.

**Admin Portal**
- Manage all tickets in one queue.
- Filter by status, category, priority, and assignee.
- Use AI-generated ticket classifications and reply drafts.
- Edit and send replies, add internal notes, and resolve tickets.
- Monitor support metrics and AI usage.

## 2. Tech Stack

- **Frontend:** React 19, Vite, Tailwind CSS 4, React Router, Axios
- **Backend:** Python 3.14, FastAPI, Pydantic, Uvicorn
- **Database:** MongoDB Atlas
- **Authentication:** JWT, bcrypt, HTTP-only cookies
- **AI:** Groq API with `openai/gpt-oss-20b` for classification and `openai/gpt-oss-120b` for reply generation
- **Testing:** pytest, httpx

## 3. How It Works

1. Authors log in and submit support tickets.
2. FastAPI validates requests and stores data in MongoDB.
3. Keyword rules classify tickets immediately.
4. AI classifies ticket categories and priorities in the background.
5. AI generates reply drafts using BookLeaf policies and actual account data.
6. Admins review and send replies.
7. Authors see updates through periodic polling.

**Human review is required before any AI-generated reply is sent.** If the AI is unavailable, keyword-based classification and manual replies remain available.

## 4. Demo Accounts

**Admin**
- Email: `admin@gmail.com`
- Password: `admin123`

**Authors**

All 10 sample authors use their email addresses from the sample data and the password `author123`.

The project includes 10 authors, 18 books, and 8 demo support tickets.

> Demo credentials are for local testing only. Use secure credentials in production.

## 5. Project Structure

```text
BookLeaf/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints and access control
│   │   ├── ai/            # AI client, prompts and classification
│   │   ├── core/          # Configuration, security and database
│   │   ├── repositories/  # Database operations
│   │   ├── schemas/       # Data validation
│   │   ├── services/      # Business logic
│   │   └── main.py
│   ├── scripts/seed.py
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── context/
│       ├── hooks/
│       ├── pages/
│       └── routes/
├── data/
│   └── bookleaf_sample_data.json
└── README.md
```

## 6. Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB Atlas account
- Optional: Groq API key

### Backend Setup

```bash
cd backend
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install dependencies and configure environment variables:

```bash
pip install -r requirements.txt
copy .env.example .env
```

On macOS/Linux, use `cp .env.example .env` instead of `copy`.

Configure `MONGODB_URI`, `JWT_SECRET`, and `GROQ_API_KEY` in `backend/.env`.

Load demo data into a **new or disposable database**:

```bash
python -m scripts.seed --ai
```

**Warning:** Seeding clears existing database data.

### Frontend Setup

```bash
cd ../frontend
npm install
copy .env.example .env
npm run build
```

Use `cp` instead of `copy` on macOS/Linux.

### Run the Application

```bash
cd ../backend
uvicorn app.main:app --reload
```

Open:
- Website: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

For frontend development, run `npm run dev` inside the `frontend` directory and open http://localhost:5173.

## 7. AI Workflow

The AI performs three tasks:

- **Classification:** Assigns a category, priority, and reason.
- **Reply generation:** Drafts context-aware responses using support policies and account information.
- **Fallback:** Uses keyword rules when AI services are unavailable.

The system validates classification output, logs AI usage, caches drafts, and applies retry and rate-limit handling.

## 8. API Overview

All API endpoints are under `/api/v1`.

| Endpoint | Purpose |
|---|---|
| `/auth` | Login, registration, logout and user details |
| `/books` | Retrieve author books |
| `/tickets` | Create and manage author tickets |
| `/admin/tickets` | Admin queue, replies, notes, assignment and AI drafts |
| `/health` | Service health check |

See `/docs` for the full API reference.

## 9. Testing

Run the backend tests:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The project includes 21 automated tests covering authentication, permissions, ticket workflows, classification, prompts, and payout-date calculations.

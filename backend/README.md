# SocialPilot Backend Service

FastAPI-based scalable backend service for the **SocialPilot: Social Media Scheduler & Campaign Management Platform**.

---

## 1. Tech Stack Overview

* **Framework**: Python 3.10+ / FastAPI / Uvicorn (ASGI)
* **ORM & Database**: SQLAlchemy 2.0 / PostgreSQL / Alembic
* **Document Store**: MongoDB (Motor async client) for content and rich media metadata
* **Cache & Job Broker**: Redis
* **Background Tasks**: Celery & Redis

---

## 2. Directory Structure

```
backend/
├── alembic/                 # Database migration scripts & environments
│   ├── versions/            # Migration revisions
│   ├── env.py               # Alembic runner with SQLAlchemy metadata
│   └── script.py.mako       # Migration template
├── app/
│   ├── api/                 # API controllers and dependencies
│   │   ├── deps.py          # Auth and DB dependency injections
│   │   └── v1/
│   │       ├── api_router.py# Master v1 API router
│   │       └── health.py    # Health check endpoint (/api/v1/health)
│   ├── core/                # Core configurations & security
│   │   └── config.py        # Pydantic BaseSettings (.env reader)
│   ├── db/                  # Database connections
│   │   ├── base.py          # Aggregator for Alembic models
│   │   ├── base_class.py    # SQLAlchemy DeclarativeBase
│   │   ├── mongo.py         # Async MongoDB connection manager
│   │   ├── postgres.py      # SQLAlchemy engine & session maker
│   │   └── redis.py         # Async Redis client manager
│   ├── integrations/        # Social Media API adapters (FB, IG, LI, X, YT, PIN)
│   ├── models/              # Relational models (Postgres)
│   ├── schemas/             # Request & Response schemas (Pydantic)
│   ├── services/            # Business logic layer
│   ├── utils/               # Helpers & utility functions
│   ├── workers/             # Celery background workers & schedules
│   └── main.py              # Application entry point & lifespan manager
├── .env.example             # Template for environment configuration
├── .env                     # Local environment settings
├── alembic.ini              # Alembic configuration
├── requirements.txt         # Python package dependencies
└── README.md                # Backend documentation
```

---

## 3. Local Setup & Execution

### Prerequisites
* Python 3.10 or higher
* PostgreSQL (port 5432)
* MongoDB (port 27017)
* Redis (port 6379)

### Step 1: Create and Activate Virtual Environment
```bash
cd backend
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Linux/macOS:
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` and verify database connection strings:
```bash
cp .env.example .env
```

### Step 4: Run Database Migrations (When models are added)
```bash
alembic upgrade head
```

### Step 5: Start the Backend Development Server
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 4. API Endpoints & Documentation

Once the server is running:
* **Interactive API Docs (Swagger UI)**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* **Alternative API Docs (ReDoc)**: [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
* **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
* **Root API Info**: [http://localhost:8000/](http://localhost:8000/)

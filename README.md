# SocialPilot — Social Media Management Platform

SocialPilot is an enterprise-grade, multi-tenant social media management platform built for content scheduling, campaign management, team collaboration, in-app notifications, analytics, and automated PDF & Excel reporting.

---

## Technical Stack & Architecture

### Backend Architecture
- **Framework**: FastAPI (Python 3.11) with Uvicorn ASGI server
- **Relational DB**: PostgreSQL 16 (SQLAlchemy 2.0 ORM + Alembic migrations)
- **Document DB**: MongoDB 4.4 (Motor async driver for media metadata & analytics events)
- **Caching & Broker**: Redis 7.0 (Celery task queue broker and result backend)
- **Task Queue**: Celery 5.6 for asynchronous post publishing and background jobs
- **Authentication**: OAuth 2.0 & JWT (HS256) with role-based access control (RBAC)

### Frontend Architecture
- **Framework**: React 18 with Vite 8.2 (SPA client routing with React Router v6)
- **Styling**: Modern CSS design system with CSS custom properties (variables) supporting dark/light mode
- **UI Components**: Custom tailwind-free aesthetic components, Lucide icons, responsive navigation
- **Production Web Server**: Nginx Alpine multi-stage container with client-side SPA fallback

---

## Milestone Scope & Completion Status

| Milestone / Feature | Scope & Capabilities | Status |
| :--- | :--- | :---: |
| **Milestone 1 — Core & Auth** | User Registration, JWT Login, Password Hashing, User Profiles, RBAC | **PASS** |
| **Milestone 2 — Publishing** | Post Composer, Multi-Platform Adapter Pipeline, Media Uploads (JPEG/PNG/WebP/MP4), Celery Task Scheduling | **PASS** |
| **Milestone 3 — Collaboration** | Workspaces/Teams, Member Invitations, Role Management, Audit Logging, Workspace Isolation | **PASS** |
| **Milestone 4 Step 1 — Discovery** | Requirement Analysis, Architecture Mapping, UI Navigation | **PASS** |
| **Milestone 4 Step 2 — Campaigns** | Campaign CRUD, Status Lifecycle (Draft, Active, Paused, Completed), Post Linkage, Color Tagging | **PASS** |
| **Milestone 4 Step 3 — Analytics** | Internal Publishing Metrics, Best Time to Post Algorithm, Platform Metrics, Performance Over Time | **PASS WITH LIMITATIONS** |
| **Milestone 4 Step 4 — Notifications**| Real-Time Event Alerts, Unread Counters, Mark Read/All, Team Notification Preference Scoping | **PASS** |
| **Milestone 4 Step 5 — Reports** | Automated PDF Reports (ReportLab) & Excel Spreadsheets (OpenPyXL) with exact analytics parity | **PASS** |
| **Milestone 4 Step 6 — Docker** | 6-Service Docker Compose Orchestration, Healthchecks, Nginx SPA Reverse Proxy | **PASS** |

---

## Local Development & Docker Setup

### Prerequisites
- Docker Desktop (with WSL2 engine on Windows)
- Python 3.11+ (for local test suite execution)
- Node.js 20+ (for local frontend development)

### Environment Configuration
Copy the template environment file:
```bash
cp .env.example .env
```

### Docker Compose Quickstart
To launch the full 6-service application stack in Docker:
```bash
# Validate configuration
docker compose config

# Build and start all 6 services in detached mode
docker compose up -d

# Verify container status and health
docker compose ps
```

Access the application:
- **Frontend SPA**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000/api/v1`
- **API Health Check**: `http://localhost:8000/health`
- **API Interactive Docs**: `http://localhost:8000/docs`

---

## Testing & Quality Assurance

### Running Backend Tests
Execute the complete backend test suite (126 tests) via virtualenv Python:
```bash
cd backend
python -m pytest -v
```

### Building Frontend Production Bundle
Validate Vite production build:
```bash
cd frontend
npm run build
```

---

## External Provider Metrics Limitation

> [!NOTE]
> **External Engagement Metrics Limitation**:
> Real-time external social media metrics (live likes, impressions, external follower counts from Meta, X, LinkedIn, YouTube, Pinterest) require live registered developer app credentials and platform OAuth access tokens.
> In accordance with project specifications, external provider metrics are clearly flagged as unavailable in the UI and reports unless official credentials are configured in `.env`. Internal publishing analytics and post metrics remain fully operational and verified.

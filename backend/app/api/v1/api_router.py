from fastapi import APIRouter
from app.api.v1 import health, auth, users, accounts, oauth
from app.api.v1.endpoints import media, posts, teams, invitations, campaigns, analytics, notifications, reports

api_router = APIRouter()

# Core health endpoint
api_router.include_router(health.router, tags=["Health"])

# Milestone 1 Core Modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["Social Accounts"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["OAuth 2.0"])

# Milestone 2 Core Modules
api_router.include_router(media.router, tags=["Media Management"])
api_router.include_router(posts.router, prefix="/posts", tags=["Posts & Scheduling"])

# Milestone 3 Collaboration Modules
api_router.include_router(teams.router, prefix="/teams", tags=["Teams"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["Team Invitations"])

# Milestone 4 Campaign, Analytics, Notifications & Reports Modules
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user, require_roles
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve profile settings of the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse, summary="Update user profile")
def update_user_profile(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update permitted profile fields (e.g. full_name).
    Sensitive attributes (id, email, role, is_active, password) are protected against modification.
    """
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


# RBAC Role Verification Test Endpoints
@router.get("/rbac/admin-only", summary="Endpoint restricted to Administrator role")
def admin_only_endpoint(
    current_user: User = Depends(require_roles(UserRole.ADMINISTRATOR))
):
    return {"message": "Access granted: Administrator", "user_id": current_user.id, "role": current_user.role}


@router.get("/rbac/marketing-only", summary="Endpoint restricted to Marketing Team and Administrator")
def marketing_endpoint(
    current_user: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.MARKETING_TEAM))
):
    return {"message": "Access granted: Marketing Team", "user_id": current_user.id, "role": current_user.role}


@router.get("/rbac/business-only", summary="Endpoint restricted to Business User and Administrator")
def business_endpoint(
    current_user: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.BUSINESS_USER))
):
    return {"message": "Access granted: Business User", "user_id": current_user.id, "role": current_user.role}


@router.get("/rbac/creator-only", summary="Endpoint restricted to Content Creator and Administrator")
def creator_endpoint(
    current_user: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.CONTENT_CREATOR))
):
    return {"message": "Access granted: Content Creator", "user_id": current_user.id, "role": current_user.role}

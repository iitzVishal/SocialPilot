from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user
from app.db.mongo import get_mongo_db
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamMemberCreate,
    TeamMemberUpdate,
    TeamMemberResponse,
)
from app.services.team_service import TeamService
from app.schemas.team_invitation import TeamInvitationCreate, TeamInvitationResponse
from app.services.invitation_service import InvitationService
from app.services.audit_service import AuditService

router = APIRouter()

@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_in: TeamCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Create a new team/workspace."""
    team = TeamService.create_team(db=db, user=current_user, team_in=team_in)
    await AuditService.log_event(
        mongo_db=mongo_db,
        team_id=team.id,
        action="team_create",
        entity_type="team",
        entity_id=team.id,
        description=f"{current_user.full_name or current_user.email} created workspace '{team.name}'",
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email
    )
    return team

@router.get("", response_model=List[TeamResponse])
def list_teams(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve all teams/workspaces where user is owner or member."""
    return TeamService.get_teams_for_user(db=db, user=current_user)

@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Fetch details of a single team by ID."""
    return TeamService.get_team_by_id(db=db, team_id=team_id, user=current_user)

@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_in: TeamUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Update team details."""
    team = TeamService.update_team(db=db, team_id=team_id, user=current_user, team_in=team_in)
    await AuditService.log_event(
        mongo_db=mongo_db,
        team_id=team.id,
        action="team_update",
        entity_type="team",
        entity_id=team.id,
        description=f"{current_user.full_name or current_user.email} updated workspace details",
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email,
        metadata={"updated_fields": [k for k, v in team_in.model_dump(exclude_unset=True).items()]}
    )
    return team

@router.delete("/{team_id}", status_code=status.HTTP_200_OK)
def delete_team(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a team/workspace."""
    TeamService.delete_team(db=db, team_id=team_id, user=current_user)
    return {"message": "Team deleted successfully", "id": team_id, "success": True}

# ── Member Management endpoints ──

@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
def list_team_members(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List members of a team."""
    return TeamService.get_team_members(db=db, team_id=team_id, user=current_user)

@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: int,
    member_in: TeamMemberCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Add a new member to the team."""
    member = TeamService.add_team_member(db=db, team_id=team_id, user=current_user, member_in=member_in)
    await AuditService.log_event(
        mongo_db=mongo_db,
        team_id=team_id,
        action="member_add",
        entity_type="team_member",
        entity_id=member.user_id,
        description=f"{current_user.full_name or current_user.email} added {member_in.email} to workspace as {member_in.role.value}",
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email,
        metadata={"invited_email": member_in.email, "role": member_in.role.value}
    )
    return member

@router.put("/{team_id}/members/{user_id}", response_model=TeamMemberResponse)
async def update_team_member_role(
    team_id: int,
    user_id: int,
    member_in: TeamMemberUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Update a team member's role."""
    member = TeamService.update_team_member_role(
        db=db, team_id=team_id, target_user_id=user_id, user=current_user, member_in=member_in
    )
    target_user = db.query(User).filter_by(id=user_id).first()
    target_name = (target_user.full_name or target_user.email) if target_user else f"User #{user_id}"
    await AuditService.log_event(
        mongo_db=mongo_db,
        team_id=team_id,
        action="member_role_change",
        entity_type="team_member",
        entity_id=user_id,
        description=f"{current_user.full_name or current_user.email} changed {target_name}'s role to {member_in.role.value}",
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email,
        metadata={"target_user_id": user_id, "new_role": member_in.role.value}
    )
    return member

@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_team_member(
    team_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Remove a member from the team."""
    target_user = db.query(User).filter_by(id=user_id).first()
    target_name = (target_user.full_name or target_user.email) if target_user else f"User #{user_id}"
    is_self = current_user.id == user_id
    TeamService.remove_team_member(db=db, team_id=team_id, target_user_id=user_id, user=current_user)
    desc = f"{current_user.full_name or current_user.email} left the workspace" if is_self else f"{current_user.full_name or current_user.email} removed {target_name} from workspace"
    await AuditService.log_event(
        mongo_db=mongo_db,
        team_id=team_id,
        action="member_remove",
        entity_type="team_member",
        entity_id=user_id,
        description=desc,
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email,
        metadata={"target_user_id": user_id, "is_self": is_self}
    )
    return {"message": "Member removed from team successfully", "user_id": user_id, "success": True}


# ── Team Invitations ──

@router.post("/{team_id}/invitations", response_model=TeamInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_team_invitation(
    team_id: int,
    invite_in: TeamInvitationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Create a new team invitation."""
    inv = InvitationService.create_invitation(
        db=db, team_id=team_id, user=current_user, invite_in=invite_in
    )
    await AuditService.log_event(
        mongo_db=mongo_db,
        team_id=team_id,
        action="invitation_create",
        entity_type="team_invitation",
        entity_id=inv.id,
        description=f"{current_user.full_name or current_user.email} invited {invite_in.email} to join workspace as {invite_in.role.value}",
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email,
        metadata={"invite_email": invite_in.email, "role": invite_in.role.value}
    )
    return inv


@router.get("/{team_id}/invitations", response_model=List[TeamInvitationResponse])
def list_team_invitations(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List invitations for a team."""
    return InvitationService.list_invitations(
        db=db, team_id=team_id, user=current_user
    )


@router.post("/{team_id}/invitations/{invitation_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_team_invitation(
    team_id: int,
    invitation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Cancel a pending team invitation."""
    InvitationService.cancel_invitation(
        db=db, team_id=team_id, invitation_id=invitation_id, user=current_user
    )
    await AuditService.log_event(
        mongo_db=mongo_db,
        team_id=team_id,
        action="invitation_cancel",
        entity_type="team_invitation",
        entity_id=invitation_id,
        description=f"{current_user.full_name or current_user.email} cancelled team invitation #{invitation_id}",
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email,
        metadata={"invitation_id": invitation_id}
    )
    return {"message": "Invitation cancelled successfully", "success": True}


# ── Team Activity Audit Feed ──

@router.get("/{team_id}/activity", status_code=status.HTTP_200_OK)
async def get_team_activity(
    team_id: int,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Retrieve paginated activity log feed for a workspace."""
    TeamService.get_team_by_id(db=db, team_id=team_id, user=current_user)
    return await AuditService.get_team_activity(mongo_db=mongo_db, team_id=team_id, page=page, limit=limit)


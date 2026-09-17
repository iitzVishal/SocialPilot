import hashlib
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user
from app.db.mongo import get_mongo_db
from app.models.user import User
from app.models.team_invitation import TeamInvitation
from app.models.team import Team
from app.models.enums import TeamInvitationStatus
from app.schemas.team_invitation import TeamInvitationResponse
from app.services.invitation_service import InvitationService
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/{token}", response_model=TeamInvitationResponse)
def get_invitation_by_token(
    token: str,
    db: Session = Depends(get_db)
):
    """Retrieve details of an invitation by token (public endpoint)."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    inv = db.query(TeamInvitation).filter_by(token_hash=token_hash).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    if inv.status != TeamInvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation is not active (status: {inv.status.value})"
        )
    return inv


@router.post("/{token}/accept", status_code=status.HTTP_200_OK)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Accept an invitation."""
    member = InvitationService.accept_invitation(db=db, token=token, user=current_user)
    await AuditService.log_event(
        mongo_db=mongo_db,
        team_id=member.team_id,
        action="invitation_accept",
        entity_type="team_invitation",
        entity_id=member.team_id,
        description=f"{current_user.full_name or current_user.email} accepted invitation to join workspace",
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email,
        metadata={"role": member.role.value}
    )
    return {"message": "Invitation accepted successfully", "team_id": member.team_id, "success": True}


@router.post("/{token}/reject", status_code=status.HTTP_200_OK)
async def reject_invitation(
    token: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """Reject an invitation."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    inv = db.query(TeamInvitation).filter_by(token_hash=token_hash).first()
    team_id = inv.team_id if inv else None

    InvitationService.reject_invitation(db=db, token=token, user=current_user)
    if team_id:
        await AuditService.log_event(
            mongo_db=mongo_db,
            team_id=team_id,
            action="invitation_reject",
            entity_type="team_invitation",
            entity_id=team_id,
            description=f"{current_user.full_name or current_user.email} rejected invitation to join workspace",
            actor_id=current_user.id,
            actor_name=current_user.full_name or current_user.email
        )
    return {"message": "Invitation rejected successfully", "success": True}


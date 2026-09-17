import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.team_invitation import TeamInvitation
from app.models.enums import UserRole, TeamInvitationStatus, NotificationType
from app.models.user import User
from app.schemas.team_invitation import TeamInvitationCreate
from app.services.notification_service import NotificationService



class InvitationService:
    @staticmethod
    def _is_team_manager(db: Session, team_id: int, user: User) -> bool:
        """Helper to check if a user is team owner, admin or system-wide admin."""
        if user.role == UserRole.ADMINISTRATOR:
            return True
        team = db.query(Team).filter_by(id=team_id).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        if team.owner_id == user.id:
            return True
        membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
        return membership is not None and membership.role == UserRole.ADMINISTRATOR

    @staticmethod
    def create_invitation(
        db: Session, team_id: int, user: User, invite_in: TeamInvitationCreate
    ) -> TeamInvitation:
        """Create a new team invitation (Owner/Admin only)."""
        # 1. Authorize requester
        if not InvitationService._is_team_manager(db, team_id, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create team invitations"
            )

        # 2. Check if target user is already a member of the team
        target_user = db.query(User).filter_by(email=invite_in.email).first()
        if target_user:
            existing_member = db.query(TeamMember).filter_by(team_id=team_id, user_id=target_user.id).first()
            if existing_member:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of this team"
                )

        # 3. Handle duplicate pending invitations cleanly by canceling them
        existing_pending = db.query(TeamInvitation).filter_by(
            team_id=team_id, email=invite_in.email, status=TeamInvitationStatus.PENDING
        ).all()
        for old_invite in existing_pending:
            old_invite.status = TeamInvitationStatus.CANCELLED

        # 4. Generate token and hash
        token = secrets.token_hex(16)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        # 5. Save invitation
        inv = TeamInvitation(
            team_id=team_id,
            email=invite_in.email,
            role=invite_in.role,
            token_hash=token_hash,
            invited_by_id=user.id,
            status=TeamInvitationStatus.PENDING,
            expires_at=expires_at,
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)

        # Set raw token on the returned object so API layer can expose it (development/testing)
        inv.token = token

        # 6. Queue email task (fail-safe)
        try:
            from app.tasks.email import send_invitation_email_task
            invite_url = f"{settings.FRONTEND_URL}/invite/{token}"
            send_invitation_email_task.delay(inv.id, invite_url)
        except Exception as e:
            logger.error(f"Failed to queue invitation email task: {str(e)}")

        # 7. In-App Notification (fail-safe)
        if target_user:
            try:
                team_name = inv.team.name if inv.team else "Workspace"
                NotificationService.create_notification(
                    db=db,
                    user_id=target_user.id,
                    team_id=team_id,
                    type=NotificationType.TEAM_INVITATION,
                    title="Team Invitation",
                    message=f"You have been invited to join team '{team_name}'.",
                    link=f"/invite/{token}"
                )
            except Exception as e:
                logger.error(f"Failed to create in-app invitation notification: {str(e)}")

        return inv

    @staticmethod
    def list_invitations(db: Session, team_id: int, user: User) -> List[TeamInvitation]:
        """List invitations for a team (Owner/Admin only)."""
        if not InvitationService._is_team_manager(db, team_id, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to list team invitations"
            )
        return db.query(TeamInvitation).filter_by(team_id=team_id).all()

    @staticmethod
    def accept_invitation(db: Session, token: str, user: User) -> TeamMember:
        """Accept a team invitation (authenticated user's email must match)."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        inv = db.query(TeamInvitation).filter_by(token_hash=token_hash).first()
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )

        # Check expiration status
        if inv.status == TeamInvitationStatus.PENDING and datetime.now(timezone.utc) > inv.expires_at:
            inv.status = TeamInvitationStatus.EXPIRED
            db.commit()

        if inv.status != TeamInvitationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation is not active (status: {inv.status.value})"
            )

        # Verify email match
        if user.email.lower() != inv.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your email does not match this invitation"
            )

        # Create member or use existing
        existing_member = db.query(TeamMember).filter_by(team_id=inv.team_id, user_id=user.id).first()
        if existing_member:
            inv.status = TeamInvitationStatus.ACCEPTED
            inv.accepted_at = datetime.now(timezone.utc)
            db.commit()
            return existing_member

        member = TeamMember(
            team_id=inv.team_id,
            user_id=user.id,
            role=inv.role
        )
        db.add(member)
        inv.status = TeamInvitationStatus.ACCEPTED
        inv.accepted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(member)

        # In-App Notification to inviter
        if inv.invited_by_id:
            try:
                NotificationService.create_notification(
                    db=db,
                    user_id=inv.invited_by_id,
                    team_id=inv.team_id,
                    type=NotificationType.INVITATION_ACCEPTED,
                    title="Invitation Accepted",
                    message=f"{user.full_name or user.email} accepted the invitation to join your workspace.",
                    link=f"/dashboard/teams/{inv.team_id}"
                )
            except Exception as e:
                logger.error(f"Failed to notify inviter on acceptance: {str(e)}")

        return member

    @staticmethod
    def reject_invitation(db: Session, token: str, user: User) -> None:
        """Reject a team invitation."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        inv = db.query(TeamInvitation).filter_by(token_hash=token_hash).first()
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )

        # Check expiration status
        if inv.status == TeamInvitationStatus.PENDING and datetime.now(timezone.utc) > inv.expires_at:
            inv.status = TeamInvitationStatus.EXPIRED
            db.commit()

        if inv.status != TeamInvitationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation is not active (status: {inv.status.value})"
            )

        # Verify email match
        if user.email.lower() != inv.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your email does not match this invitation"
            )

        inv.status = TeamInvitationStatus.REJECTED
        db.commit()

    @staticmethod
    def cancel_invitation(db: Session, team_id: int, invitation_id: int, user: User) -> None:
        """Cancel a pending team invitation (Owner/Admin only)."""
        if not InvitationService._is_team_manager(db, team_id, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel team invitations"
            )

        inv = db.query(TeamInvitation).filter_by(id=invitation_id, team_id=team_id).first()
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )

        if inv.status != TeamInvitationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending invitations can be cancelled"
            )

        inv.status = TeamInvitationStatus.CANCELLED
        db.commit()

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.enums import UserRole, NotificationType
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.schemas.team import TeamCreate, TeamUpdate, TeamMemberCreate, TeamMemberUpdate
from app.services.notification_service import NotificationService


class TeamService:

    @staticmethod
    def create_team(db: Session, user: User, team_in: TeamCreate) -> Team:
        """Create a new team, assigning the current user as owner and default admin member."""
        # Create the team
        team = Team(
            name=team_in.name,
            description=team_in.description,
            owner_id=user.id,
            require_post_approval=team_in.require_post_approval if team_in.require_post_approval is not None else False
        )
        db.add(team)
        db.flush()  # get team.id

        # Auto-create team member membership for owner
        owner_membership = TeamMember(
            team_id=team.id,
            user_id=user.id,
            role=UserRole.ADMINISTRATOR
        )
        db.add(owner_membership)
        db.commit()
        db.refresh(team)
        return team

    @staticmethod
    def get_teams_for_user(db: Session, user: User) -> List[Team]:
        """List all teams that the user is the owner of or a member of."""
        if user.role == UserRole.ADMINISTRATOR:
            return db.query(Team).all()

        return db.query(Team).outerjoin(TeamMember).filter(
            (Team.owner_id == user.id) | (TeamMember.user_id == user.id)
        ).distinct().all()

    @staticmethod
    def get_team_by_id(db: Session, team_id: int, user: User) -> Team:
        """Retrieve a single team by ID, checking authorization (owner, member, or sysadmin)."""
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        # Access check
        is_owner = team.owner_id == user.id
        is_sysadmin = user.role == UserRole.ADMINISTRATOR
        membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()

        if not (is_owner or is_sysadmin or membership):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this team"
            )

        return team

    @staticmethod
    def update_team(db: Session, team_id: int, user: User, team_in: TeamUpdate) -> Team:
        """Update a team's metadata (only allowed for owner or system admin)."""
        team = TeamService.get_team_by_id(db, team_id, user)

        if team.owner_id != user.id and user.role != UserRole.ADMINISTRATOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the team owner can update the team details"
            )

        if team_in.name is not None:
            team.name = team_in.name
        if team_in.description is not None:
            team.description = team_in.description
        if team_in.require_post_approval is not None:
            team.require_post_approval = team_in.require_post_approval

        db.commit()
        db.refresh(team)
        return team

    @staticmethod
    def delete_team(db: Session, team_id: int, user: User) -> bool:
        """Delete a team (only allowed for owner or system admin)."""
        team = TeamService.get_team_by_id(db, team_id, user)

        if team.owner_id != user.id and user.role != UserRole.ADMINISTRATOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the team owner can delete the team"
            )

        db.delete(team)
        db.commit()
        return True

    @staticmethod
    def get_team_members(db: Session, team_id: int, user: User) -> List[TeamMember]:
        """List all memberships in a team."""
        TeamService.get_team_by_id(db, team_id, user)  # Verify access to the team
        return db.query(TeamMember).filter_by(team_id=team_id).all()

    @staticmethod
    def add_team_member(db: Session, team_id: int, user: User, member_in: TeamMemberCreate) -> TeamMember:
        """Add a user by email to the team (requires owner, team admin, or system admin privileges)."""
        team = TeamService.get_team_by_id(db, team_id, user)

        # Check authorization
        requester_membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
        is_team_admin = requester_membership and requester_membership.role == UserRole.ADMINISTRATOR
        is_owner = team.owner_id == user.id
        is_sysadmin = user.role == UserRole.ADMINISTRATOR

        if not (is_owner or is_team_admin or is_sysadmin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add members to this team"
            )

        # Lookup target user by email
        target_user = db.query(User).filter_by(email=member_in.email).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email not found"
            )

        # Check duplicate membership
        existing_membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=target_user.id).first()
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this team"
            )

        # Create member record
        member = TeamMember(
            team_id=team_id,
            user_id=target_user.id,
            role=member_in.role
        )
        db.add(member)
        db.commit()
        db.refresh(member)

        # In-App Notification (fail-safe)
        try:
            NotificationService.create_notification(
                db=db,
                user_id=target_user.id,
                team_id=team_id,
                type=NotificationType.TEAM_MEMBER_ADDED,
                title="Added to Team",
                message=f"You have been added to team '{team.name}'.",
                link=f"/dashboard/teams/{team_id}"
            )
        except Exception as e:
            logger.error(f"Failed to create notification on member add: {e}")

        return member

    @staticmethod
    def update_team_member_role(
        db: Session, team_id: int, target_user_id: int, user: User, member_in: TeamMemberUpdate
    ) -> TeamMember:
        """Update a team member's role (requires owner, team admin, or system admin privileges)."""
        team = TeamService.get_team_by_id(db, team_id, user)

        # Find target member
        member = db.query(TeamMember).filter_by(team_id=team_id, user_id=target_user_id).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )

        # Check authorization
        requester_membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
        is_team_admin = requester_membership and requester_membership.role == UserRole.ADMINISTRATOR
        is_owner = team.owner_id == user.id
        is_sysadmin = user.role == UserRole.ADMINISTRATOR

        if not (is_owner or is_team_admin or is_sysadmin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update roles in this team"
            )

        # Owner role cannot be modified by anyone
        if target_user_id == team.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify team owner's role"
            )

        # Update role
        member.role = member_in.role
        db.commit()
        db.refresh(member)

        # In-App Notification (fail-safe)
        try:
            NotificationService.create_notification(
                db=db,
                user_id=target_user_id,
                team_id=team_id,
                type=NotificationType.ROLE_CHANGED,
                title="Role Updated",
                message=f"Your role in team '{team.name}' was updated to '{member_in.role.value}'.",
                link=f"/dashboard/teams/{team_id}"
            )
        except Exception as e:
            logger.error(f"Failed to create notification on role change: {e}")

        return member

    @staticmethod
    def remove_team_member(db: Session, team_id: int, target_user_id: int, user: User) -> bool:
        """Remove a user from the team (allowed for self-leaving, owner, team admin, or system admin)."""
        team = TeamService.get_team_by_id(db, team_id, user)

        # Find member
        member = db.query(TeamMember).filter_by(team_id=team_id, user_id=target_user_id).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )

        # Owner cannot be removed from the team
        if target_user_id == team.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the team owner from the team"
            )

        # Check authorization
        is_self = target_user_id == user.id
        requester_membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
        is_team_admin = requester_membership and requester_membership.role == UserRole.ADMINISTRATOR
        is_owner = team.owner_id == user.id
        is_sysadmin = user.role == UserRole.ADMINISTRATOR

        if not (is_self or is_owner or is_team_admin or is_sysadmin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to remove members from this team"
            )

        db.delete(member)
        db.commit()

        # In-App Notification (fail-safe)
        try:
            NotificationService.create_notification(
                db=db,
                user_id=target_user_id,
                team_id=team_id,
                type=NotificationType.TEAM_MEMBER_REMOVED,
                title="Removed from Team",
                message=f"You were removed from team '{team.name}'.",
                link="/dashboard/teams"
            )
        except Exception as e:
            logger.error(f"Failed to create notification on member remove: {e}")

        return True

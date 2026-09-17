from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.api.deps import get_db, get_current_active_user
from app.db.mongo import get_mongo_db
from app.models.user import User
from app.models.enums import PostStatus, SocialPlatform
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostScheduleRequest,
    PostResponse,
    AccountPublishResult,
    PostRejectRequest,
)
from app.services.post_service import PostService
from app.tasks.publishing import publish_post_task, cancel_scheduled_task

router = APIRouter()


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_in: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """
    Create a new post as DRAFT, SCHEDULED, or QUEUED for immediate publishing.
    Dispatches Celery background task if scheduled or published immediately.
    """
    post_doc = await PostService.create_post(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_in=post_in
    )
    post_id = post_doc["id"]

    # If publish_now requested, dispatch Celery task immediately
    if post_in.publish_now:
        task = publish_post_task.delay(post_id=post_id)
        # Store celery task ID
        await mongo_db["posts"].update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {"celery_task_id": task.id}}
        )
        post_doc["celery_task_id"] = task.id

    # If scheduled_at requested, schedule Celery task with ETA
    elif post_in.scheduled_at:
        task = publish_post_task.apply_async(
            args=[post_id],
            eta=post_in.scheduled_at
        )
        await mongo_db["posts"].update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {"celery_task_id": task.id}}
        )
        post_doc["celery_task_id"] = task.id

    return post_doc


@router.get("", response_model=Dict[str, Any])
async def list_posts(
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    status: Optional[PostStatus] = Query(None, description="Filter by post status"),
    platform: Optional[SocialPlatform] = Query(None, description="Filter by platform"),
    start_date: Optional[datetime] = Query(None, description="Filter from UTC date"),
    end_date: Optional[datetime] = Query(None, description="Filter to UTC date"),
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """
    Query posts with pagination and filters (status, platform, date range).
    Enforces user and team ownership authorization.
    """
    items, total = await PostService.list_posts(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        team_id=team_id,
        status_filter=status,
        platform_filter=platform,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Fetch single post by MongoDB ID with ownership authorization check."""
    return await PostService.get_post_by_id(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id
    )


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    post_in: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Update post details (only allowed in DRAFT or SCHEDULED states)."""
    return await PostService.update_post(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id,
        post_update=post_in
    )


@router.delete("/{post_id}", status_code=status.HTTP_200_OK)
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Hard-delete a DRAFT or CANCELLED post."""
    success = await PostService.delete_post(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id
    )
    return {"message": "Post deleted successfully", "id": post_id, "success": success}


@router.post("/{post_id}/schedule", response_model=PostResponse)
async def schedule_post(
    post_id: str,
    schedule_in: PostScheduleRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Transition a DRAFT post to SCHEDULED and queue delayed Celery publishing task."""
    post_doc = await PostService.schedule_post(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id,
        scheduled_at=schedule_in.scheduled_at
    )

    # Dispatch Celery task with ETA
    task = publish_post_task.apply_async(
        args=[post_id],
        eta=schedule_in.scheduled_at
    )
    await mongo_db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"celery_task_id": task.id}}
    )
    post_doc["celery_task_id"] = task.id
    return post_doc


@router.post("/{post_id}/unschedule", response_model=PostResponse)
async def unschedule_post(
    post_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Revert a SCHEDULED post back to DRAFT and cancel scheduled Celery task."""
    # Retrieve current post to get celery task id if any
    current_post = await PostService.get_post_by_id(mongo_db, db, current_user, post_id)
    task_id = current_post.get("celery_task_id")
    if task_id:
        cancel_scheduled_task.delay(task_id=task_id)

    return await PostService.unschedule_post(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id
    )


@router.post("/{post_id}/publish", response_model=PostResponse)
async def publish_post_now(
    post_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Queue a DRAFT, SCHEDULED, or FAILED post for immediate background dispatch."""
    post_doc = await PostService.queue_post_for_publish(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id
    )

    # Dispatch immediate Celery task
    task = publish_post_task.delay(post_id=post_id)
    await mongo_db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"celery_task_id": task.id}}
    )
    post_doc["celery_task_id"] = task.id
    return post_doc


@router.post("/{post_id}/cancel", response_model=PostResponse)
async def cancel_post(
    post_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Cancel a SCHEDULED or QUEUED post and revoke the background task."""
    current_post = await PostService.get_post_by_id(mongo_db, db, current_user, post_id)
    task_id = current_post.get("celery_task_id")
    if task_id:
        cancel_scheduled_task.delay(task_id=task_id)

    return await PostService.cancel_post(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id
    )


@router.get("/{post_id}/status", response_model=Dict[str, Any])
async def get_post_status(
    post_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Fetch current publishing state and per-account dispatch results."""
    post_doc = await PostService.get_post_by_id(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id
    )
    return {
        "id": post_doc["id"],
        "status": post_doc["status"],
        "scheduled_at": post_doc.get("scheduled_at"),
        "published_at": post_doc.get("published_at"),
        "celery_task_id": post_doc.get("celery_task_id"),
        "publish_results": post_doc.get("publish_results", {}),
        "target_accounts": post_doc.get("target_accounts", []),
        "target_platforms": post_doc.get("target_platforms", []),
    }


@router.post("/{post_id}/submit-for-approval", response_model=PostResponse)
async def submit_for_approval(
    post_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Submit a draft post for workspace approval."""
    return await PostService.submit_for_approval(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id
    )


@router.post("/{post_id}/approve", response_model=PostResponse)
async def approve_post(
    post_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Approve a pending post workspace-wide."""
    return await PostService.approve_post(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id
    )


@router.post("/{post_id}/reject", response_model=PostResponse)
async def reject_post(
    post_id: str,
    reject_in: PostRejectRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """Reject a pending post with comments."""
    return await PostService.reject_post(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        post_id=post_id,
        reason=reject_in.reason
    )

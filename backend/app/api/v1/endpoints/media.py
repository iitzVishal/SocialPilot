from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_active_user, get_db
from app.db.mongo import get_mongo_db
from app.models.user import User
from app.schemas.media import MediaAssetResponse
from app.services.media_service import MediaService

router = APIRouter(prefix="/media", tags=["Media Management"])
media_service = MediaService()


@router.post("", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_media_file(
    file: UploadFile = File(..., description="Binary media file (JPEG, PNG, WebP, MP4)"),
    team_id: Optional[int] = Form(None, description="Optional team ownership context"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Upload a media asset for use in social media posts.
    Performs server-side magic byte inspection, extracts dimensions and aspect ratio,
    and returns verified media metadata.
    """
    result = await media_service.upload_media(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        file=file,
        team_id=team_id
    )
    return result


@router.get("", response_model=List[MediaAssetResponse])
async def list_media_assets(
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    List media assets owned by the authenticated user or team, ordered by newest first.
    """
    docs, _ = await media_service.list_media(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        team_id=team_id,
        skip=skip,
        limit=limit
    )
    return docs


@router.get("/{media_id}", response_model=MediaAssetResponse)
async def get_media_asset(
    media_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Fetch metadata for an uploaded media asset by its UUID.
    """
    return await media_service.get_media_by_id(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        media_id=media_id
    )


@router.delete("/{media_id}", status_code=status.HTTP_200_OK)
async def delete_media_asset(
    media_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Delete a media asset and its underlying binary file permanently.
    """
    deleted = await media_service.delete_media(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        media_id=media_id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset could not be deleted or was not found."
        )
    return {"status": "deleted", "media_id": media_id}

import io
import math
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from bson import ObjectId
from PIL import Image, UnidentifiedImageError
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.schemas.media import MediaAssetResponse
from app.services.media_storage.base import BaseStorageService
from app.services.media_storage.local import LocalStorageService

logger = logging.getLogger(__name__)

# Default storage service instance
default_storage_service = LocalStorageService(
    base_dir=settings.MEDIA_UPLOAD_DIR,
    url_prefix="/uploads/media"
)


def compute_aspect_ratio_str(width: int, height: int) -> str:
    """Compute a human-readable aspect ratio string (e.g. 1:1, 16:9, 4:5, 1.91:1)."""
    if width <= 0 or height <= 0:
        return "unknown"
    ratio = width / height

    # Match common social media aspect ratios within 2% tolerance
    known_ratios = [
        (1.0, "1:1"),
        (16 / 9, "16:9"),
        (9 / 16, "9:16"),
        (4 / 5, "4:5"),
        (1.91, "1.91:1"),
        (4 / 3, "4:3"),
        (3 / 4, "3:4"),
    ]
    for target_ratio, label in known_ratios:
        if abs(ratio - target_ratio) <= 0.03:
            return label

    # Fallback to simplified fraction using GCD
    gcd = math.gcd(width, height)
    simplified_w = width // gcd
    simplified_h = height // gcd
    if simplified_w <= 20 and simplified_h <= 20:
        return f"{simplified_w}:{simplified_h}"
    return f"{ratio:.2f}:1"


def _serialize_media_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert MongoDB media document to API-compatible dictionary."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


async def ensure_media_indexes(mongo_db: AsyncIOMotorDatabase) -> None:
    """Create MongoDB indexes for media_assets collection idempotently."""
    try:
        media_coll = mongo_db["media_assets"]
        await media_coll.create_index([("user_id", 1), ("created_at", -1)], name="idx_media_user_created")
        await media_coll.create_index([("media_id", 1)], unique=True, name="idx_media_uuid_unique")
        logger.info("MongoDB media_assets indexes verified/created successfully.")
    except Exception as e:
        logger.warning(f"Could not create media_assets indexes: {e}")


class MediaService:
    def __init__(self, storage_service: Optional[BaseStorageService] = None):
        self.storage = storage_service or default_storage_service

    def validate_and_extract_metadata(
        self,
        file_bytes: bytes,
        file_name: str,
        declared_content_type: str
    ) -> Dict[str, Any]:
        """
        Perform strict server-side validation of media bytes.
        Inspects magic bytes with Pillow for images and validates MP4 containers.
        Extracts width, height, aspect ratio, and verified MIME type.
        """
        file_size = len(file_bytes)
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file: Uploaded file contains 0 bytes."
            )

        # Normalize declared content type
        normalized_mime = declared_content_type.lower().split(";")[0].strip()
        if normalized_mime not in settings.MEDIA_ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported media type: '{declared_content_type}'. Allowed types: {settings.MEDIA_ALLOWED_MIME_TYPES}"
            )

        # Handle Images
        if normalized_mime.startswith("image/"):
            if file_size > settings.MEDIA_MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image file size ({file_size} bytes) exceeds maximum limit ({settings.MEDIA_MAX_IMAGE_SIZE} bytes)."
                )

            try:
                # Open with Pillow and verify image integrity
                with Image.open(io.BytesIO(file_bytes)) as img:
                    img.verify()

                # Reopen to read dimensions safely (verify closes file stream)
                with Image.open(io.BytesIO(file_bytes)) as img:
                    width, height = img.size
                    img_format = (img.format or "").upper()

                # Validate format matches MIME type
                format_mime_map = {
                    "JPEG": "image/jpeg",
                    "PNG": "image/png",
                    "WEBP": "image/webp",
                }
                actual_mime = format_mime_map.get(img_format)
                if not actual_mime or actual_mime != normalized_mime:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Image content mismatch: Declared '{normalized_mime}' but actual file format is '{img_format}'."
                    )

                aspect_ratio = compute_aspect_ratio_str(width, height)
                return {
                    "mime_type": actual_mime,
                    "file_size": file_size,
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio,
                    "duration_seconds": None,
                }

            except (UnidentifiedImageError, ValueError, OSError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Corrupt or invalid image file: {str(e)}"
                )

        # Handle Videos
        elif normalized_mime.startswith("video/"):
            if file_size > settings.MEDIA_MAX_VIDEO_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Video file size ({file_size} bytes) exceeds maximum limit ({settings.MEDIA_MAX_VIDEO_SIZE} bytes)."
                )

            # Validate MP4 magic signature (bytes 4-8 contain 'ftyp')
            if len(file_bytes) < 12 or b"ftyp" not in file_bytes[4:12]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or corrupt video file: Missing MP4 signature."
                )

            return {
                "mime_type": normalized_mime,
                "file_size": file_size,
                "width": None,
                "height": None,
                "aspect_ratio": None,
                "duration_seconds": None,
            }

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media MIME type: {normalized_mime}"
        )

    async def upload_media(
        self,
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        file: UploadFile,
        team_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate, store binary file, and persist metadata to MongoDB.
        Performs automatic cleanup if MongoDB insert fails.
        """
        # Verify team authorization if team_id is provided
        if team_id:
            team = db.query(Team).filter(Team.id == team_id).first()
            if not team:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team {team_id} not found")
            is_team_owner = team.owner_id == user.id
            membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
            if not (is_team_owner or membership or user.role.value == "administrator"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to team media")

        file_bytes = await file.read()
        file_name = file.filename or "media_file"
        content_type = file.content_type or "application/octet-stream"

        # Validate file and extract metadata
        metadata = self.validate_and_extract_metadata(file_bytes, file_name, content_type)

        # Save to storage layer
        storage_path, public_url = await self.storage.save_file(
            file_bytes=file_bytes,
            file_name=file_name,
            content_type=metadata["mime_type"]
        )

        media_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc)

        doc = {
            "media_id": media_id,
            "user_id": user.id,
            "team_id": team_id,
            "storage_path": storage_path,
            "public_url": public_url,
            "file_name": file_name,
            "mime_type": metadata["mime_type"],
            "file_size": metadata["file_size"],
            "width": metadata["width"],
            "height": metadata["height"],
            "aspect_ratio": metadata["aspect_ratio"],
            "duration_seconds": metadata["duration_seconds"],
            "created_at": now_utc,
        }

        try:
            res = await mongo_db["media_assets"].insert_one(doc)
            doc["_id"] = res.inserted_id
            return _serialize_media_doc(doc)
        except Exception as e:
            # Rollback: Clean up stored binary file if MongoDB persistence fails
            logger.error(f"Failed to persist media metadata to MongoDB. Rolling back stored file: {e}")
            await self.storage.delete_file(storage_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save media metadata. Upload rolled back."
            )

    async def get_media_by_id(
        self,
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        media_id: str
    ) -> Dict[str, Any]:
        """Fetch media metadata by media_id, verifying user or team ownership."""
        doc = await mongo_db["media_assets"].find_one({"media_id": media_id})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")

        is_owner = doc.get("user_id") == user.id
        is_admin = user.role.value == "administrator"
        team_id = doc.get("team_id")
        is_team_member = False
        if team_id:
            team = db.query(Team).filter(Team.id == team_id).first()
            is_team_owner = team and team.owner_id == user.id
            membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
            if is_team_owner or membership:
                is_team_member = True

        if not (is_owner or is_team_member or is_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this media asset")

        return _serialize_media_doc(doc)

    async def list_media(
        self,
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        team_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List media assets owned by the user or team, ordered by newest first."""
        query: Dict[str, Any] = {}

        if user.role.value == "administrator" and not team_id:
            pass
        elif team_id:
            team = db.query(Team).filter(Team.id == team_id).first()
            is_team_owner = team and team.owner_id == user.id
            membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
            if not (is_team_owner or membership or user.role.value == "administrator"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to team media")
            query["team_id"] = team_id
        else:
            query["user_id"] = user.id

        coll = mongo_db["media_assets"]
        total = await coll.count_documents(query)
        cursor = coll.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)

        return [_serialize_media_doc(d) for d in docs], total

    async def delete_media(
        self,
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        media_id: str
    ) -> bool:
        """Delete media asset document from MongoDB and remove physical binary from storage."""
        doc = await self.get_media_by_id(mongo_db, db, user, media_id)
        storage_path = doc.get("storage_path")

        # 1. Delete MongoDB metadata
        res = await mongo_db["media_assets"].delete_one({"media_id": media_id})
        if res.deleted_count == 0:
            return False

        # 2. Delete physical file from storage
        if storage_path:
            await self.storage.delete_file(storage_path)

        return True

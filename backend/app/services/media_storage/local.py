import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple
from fastapi import HTTPException, status
from app.services.media_storage.base import BaseStorageService


class LocalStorageService(BaseStorageService):
    """
    Local filesystem implementation of BaseStorageService for development and staging.
    Generates sanitized directory trees (YYYY/MM/<uuid>.<ext>) and enforces path traversal guards.
    """

    def __init__(self, base_dir: str = "uploads/media", url_prefix: str = "/uploads/media"):
        self.base_dir = Path(base_dir).resolve()
        self.url_prefix = url_prefix.rstrip("/")
        # Ensure base upload directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_safe_extension(self, original_filename: str, content_type: str) -> str:
        """Derive a safe lowercase extension from original filename or content type."""
        ext = Path(original_filename).suffix.lower()
        # Clean extension (letters/numbers only)
        clean_ext = "".join(c for c in ext if c.isalnum() or c == ".")
        if clean_ext and clean_ext.startswith("."):
            return clean_ext

        # Fallback mapping from MIME
        mime_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
        }
        return mime_map.get(content_type.lower(), ".bin")

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path and verify it stays strictly inside base_dir to prevent path traversal."""
        resolved = (self.base_dir / relative_path).resolve()
        if not str(resolved).startswith(str(self.base_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Path traversal attempt detected."
            )
        return resolved

    async def save_file(
        self,
        file_bytes: bytes,
        file_name: str,
        content_type: str,
        sub_dir: str = ""
    ) -> Tuple[str, str]:
        """
        Write file bytes to disk in date-partitioned directory.
        Returns (relative_storage_path, public_url).
        """
        now = datetime.now(timezone.utc)
        year_month = sub_dir or f"{now.year:04d}/{now.month:02d}"
        target_dir = self.base_dir / year_month
        target_dir.mkdir(parents=True, exist_ok=True)

        file_uuid = uuid.uuid4().hex
        ext = self._get_safe_extension(file_name, content_type)
        safe_filename = f"{file_uuid}{ext}"

        relative_path = f"{year_month}/{safe_filename}".replace("\\", "/")
        full_path = self._resolve_safe_path(relative_path)

        with open(full_path, "wb") as f:
            f.write(file_bytes)

        public_url = f"{self.url_prefix}/{relative_path}"
        return relative_path, public_url

    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from disk if it exists inside base_dir."""
        try:
            full_path = self._resolve_safe_path(storage_path)
            if full_path.is_file():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False

    def get_public_url(self, storage_path: str) -> str:
        clean_path = storage_path.replace("\\", "/").lstrip("/")
        return f"{self.url_prefix}/{clean_path}"

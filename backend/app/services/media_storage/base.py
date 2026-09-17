from abc import ABC, abstractmethod
from typing import Tuple


class BaseStorageService(ABC):
    """
    Abstract contract for binary media asset storage.
    Enables zero-friction replacement of local storage with AWS S3, Cloudflare R2, or GCP CS.
    """

    @abstractmethod
    async def save_file(
        self,
        file_bytes: bytes,
        file_name: str,
        content_type: str,
        sub_dir: str = ""
    ) -> Tuple[str, str]:
        """
        Persist binary file to storage.
        Returns:
            Tuple[storage_path, public_url]
        """
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """
        Delete a stored binary file from disk/object storage.
        Returns:
            True if file was deleted, False if file did not exist or could not be removed.
        """
        pass

    @abstractmethod
    def get_public_url(self, storage_path: str) -> str:
        """
        Compute or format the public-facing URL for a stored asset path.
        """
        pass

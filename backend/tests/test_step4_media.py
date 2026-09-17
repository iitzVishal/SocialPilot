import io
import os
import shutil
import tempfile
import pytest
from PIL import Image
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException, UploadFile

from app.core.config import settings
from app.db.base_class import Base
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.enums import UserRole
from app.services.media_storage.local import LocalStorageService
from app.services.media_service import MediaService, compute_aspect_ratio_str, ensure_media_indexes


def create_test_image(format_name: str, width: int = 200, height: int = 200) -> bytes:
    """Helper to generate valid image bytes in-memory using Pillow."""
    img = Image.new("RGB", (width, height), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


def create_test_mp4_bytes() -> bytes:
    """Helper to create minimal valid MP4 container header bytes."""
    # 4 bytes size (0x00000018 = 24 bytes), 4 bytes 'ftyp', 4 bytes 'mp42', 4 bytes minor_ver, 8 bytes compatible brands
    return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42" + (b"\x00" * 100)


@pytest.fixture
def temp_upload_dir():
    temp_dir = tempfile.mkdtemp(prefix="socialpilot_test_uploads_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def local_storage(temp_upload_dir):
    return LocalStorageService(base_dir=temp_upload_dir, url_prefix="/uploads/media")


@pytest.fixture
def media_service(local_storage):
    return MediaService(storage_service=local_storage)


@pytest.fixture
def mongo_test_db():
    client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
    db = client["socialpilot_test_mongo"]
    yield db
    client.close()


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def user_a(db_session):
    import uuid
    uid = uuid.uuid4().hex[:6]
    user = User(
        email=f"user_a_{uid}@socialpilot.test",
        hashed_password="hashed_password",
        full_name="User A",
        role=UserRole.CONTENT_CREATOR,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session):
    import uuid
    uid = uuid.uuid4().hex[:6]
    user = User(
        email=f"user_b_{uid}@socialpilot.test",
        hashed_password="hashed_password",
        full_name="User B",
        role=UserRole.CONTENT_CREATOR,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# --- Tests A, B, C, D: Valid Media Formats ---

@pytest.mark.asyncio
async def test_a_valid_jpeg_upload(media_service, mongo_test_db, db_session, user_a, temp_upload_dir):
    """Test A: Valid JPEG upload, Pillow dimension inspection, MongoDB persistence, and disk storage."""
    await mongo_test_db["media_assets"].delete_many({})
    await ensure_media_indexes(mongo_test_db)

    jpeg_bytes = create_test_image("JPEG", width=800, height=800)
    upload_file = UploadFile(
        file=io.BytesIO(jpeg_bytes),
        filename="hero_banner.jpg",
        headers={"content-type": "image/jpeg"}
    )

    result = await media_service.upload_media(mongo_test_db, db_session, user_a, upload_file)
    assert result["media_id"] is not None
    assert result["file_name"] == "hero_banner.jpg"
    assert result["mime_type"] == "image/jpeg"
    assert result["width"] == 800
    assert result["height"] == 800
    assert result["aspect_ratio"] == "1:1"
    assert result["public_url"].startswith("/uploads/media/")

    # Test M: Verify physical file exists on disk
    full_disk_path = os.path.join(temp_upload_dir, result["storage_path"])
    assert os.path.isfile(full_disk_path)
    assert os.path.getsize(full_disk_path) == len(jpeg_bytes)


@pytest.mark.asyncio
async def test_b_valid_png_upload(media_service, mongo_test_db, db_session, user_a):
    """Test B: Valid PNG upload with aspect ratio calculation (16:9)."""
    png_bytes = create_test_image("PNG", width=1920, height=1080)
    upload_file = UploadFile(
        file=io.BytesIO(png_bytes),
        filename="screen.png",
        headers={"content-type": "image/png"}
    )
    result = await media_service.upload_media(mongo_test_db, db_session, user_a, upload_file)
    assert result["mime_type"] == "image/png"
    assert result["width"] == 1920
    assert result["height"] == 1080
    assert result["aspect_ratio"] == "16:9"


@pytest.mark.asyncio
async def test_c_valid_webp_upload(media_service, mongo_test_db, db_session, user_a):
    """Test C: Valid WebP upload."""
    webp_bytes = create_test_image("WEBP", width=600, height=750)
    upload_file = UploadFile(
        file=io.BytesIO(webp_bytes),
        filename="portrait.webp",
        headers={"content-type": "image/webp"}
    )
    result = await media_service.upload_media(mongo_test_db, db_session, user_a, upload_file)
    assert result["mime_type"] == "image/webp"
    assert result["width"] == 600
    assert result["height"] == 750
    assert result["aspect_ratio"] == "4:5"


@pytest.mark.asyncio
async def test_d_valid_mp4_upload(media_service, mongo_test_db, db_session, user_a):
    """Test D: Valid MP4 container upload with magic bytes verification."""
    mp4_bytes = create_test_mp4_bytes()
    upload_file = UploadFile(
        file=io.BytesIO(mp4_bytes),
        filename="promo.mp4",
        headers={"content-type": "video/mp4"}
    )
    result = await media_service.upload_media(mongo_test_db, db_session, user_a, upload_file)
    assert result["mime_type"] == "video/mp4"
    assert result["file_size"] == len(mp4_bytes)


# --- Tests E, F, G, H, I: Validation Errors & Rejections ---

def test_e_content_mismatch_rejection(media_service):
    """Test E: PNG bytes sent with declared image/jpeg MIME type are rejected."""
    png_bytes = create_test_image("PNG", width=100, height=100)
    with pytest.raises(HTTPException) as exc_info:
        media_service.validate_and_extract_metadata(png_bytes, "fake.jpg", "image/jpeg")
    assert exc_info.value.status_code == 400
    assert "Image content mismatch" in exc_info.value.detail


def test_f_corrupt_image_rejection(media_service):
    """Test F: Corrupt/random binary bytes are rejected by Pillow."""
    garbage_bytes = b"NOT_AN_IMAGE_RANDOM_GARBAGE_BYTES_12345"
    with pytest.raises(HTTPException) as exc_info:
        media_service.validate_and_extract_metadata(garbage_bytes, "broken.jpg", "image/jpeg")
    assert exc_info.value.status_code == 400
    assert "Corrupt or invalid image file" in exc_info.value.detail


def test_g_empty_file_rejection(media_service):
    """Test G: 0-byte upload is rejected."""
    with pytest.raises(HTTPException) as exc_info:
        media_service.validate_and_extract_metadata(b"", "empty.jpg", "image/jpeg")
    assert exc_info.value.status_code == 400
    assert "Empty file" in exc_info.value.detail


def test_h_oversized_file_rejection(media_service):
    """Test H: File exceeding size limit is rejected."""
    oversized_bytes = b"X" * (settings.MEDIA_MAX_IMAGE_SIZE + 1024)
    with pytest.raises(HTTPException) as exc_info:
        media_service.validate_and_extract_metadata(oversized_bytes, "huge.jpg", "image/jpeg")
    assert exc_info.value.status_code == 400
    assert "exceeds maximum limit" in exc_info.value.detail


def test_i_unsupported_media_type_rejection(media_service):
    """Test I: PDF or other non-media files are rejected."""
    pdf_bytes = b"%PDF-1.4 header..."
    with pytest.raises(HTTPException) as exc_info:
        media_service.validate_and_extract_metadata(pdf_bytes, "document.pdf", "application/pdf")
    assert exc_info.value.status_code == 400
    assert "Unsupported media type" in exc_info.value.detail


# --- Tests J, K: Dimension & Aspect Ratio Calculations ---

def test_j_and_k_aspect_ratio_calculations():
    """Test J & K: Unit tests for aspect ratio computation logic."""
    assert compute_aspect_ratio_str(1080, 1080) == "1:1"
    assert compute_aspect_ratio_str(1920, 1080) == "16:9"
    assert compute_aspect_ratio_str(1080, 1920) == "9:16"
    assert compute_aspect_ratio_str(1080, 1350) == "4:5"
    assert compute_aspect_ratio_str(1200, 628) == "1.91:1"
    assert compute_aspect_ratio_str(800, 600) == "4:3"


# --- Tests L, N, O, P, Q: Authorization, Retrieval, Deletion & Cleanup ---

@pytest.mark.asyncio
async def test_l_and_n_listing_authorization(media_service, mongo_test_db, db_session, user_a, user_b):
    """Test L & N: Media assets persisted in MongoDB and listed with user isolation."""
    await mongo_test_db["media_assets"].delete_many({})

    # User A uploads 2 files
    img_a1 = create_test_image("JPEG", 100, 100)
    await media_service.upload_media(
        mongo_test_db, db_session, user_a,
        UploadFile(file=io.BytesIO(img_a1), filename="a1.jpg", headers={"content-type": "image/jpeg"})
    )
    img_a2 = create_test_image("PNG", 100, 100)
    await media_service.upload_media(
        mongo_test_db, db_session, user_a,
        UploadFile(file=io.BytesIO(img_a2), filename="a2.png", headers={"content-type": "image/png"})
    )

    # User B uploads 1 file
    img_b1 = create_test_image("WEBP", 100, 100)
    await media_service.upload_media(
        mongo_test_db, db_session, user_b,
        UploadFile(file=io.BytesIO(img_b1), filename="b1.webp", headers={"content-type": "image/webp"})
    )

    # User A listing sees exactly 2 assets
    list_a, count_a = await media_service.list_media(mongo_test_db, db_session, user_a)
    assert count_a == 2
    assert len(list_a) == 2

    # User B listing sees exactly 1 asset
    list_b, count_b = await media_service.list_media(mongo_test_db, db_session, user_b)
    assert count_b == 1
    assert len(list_b) == 1


@pytest.mark.asyncio
async def test_o_and_p_unauthorized_access_and_deletion(media_service, mongo_test_db, db_session, user_a, user_b):
    """Test O & P: User B cannot fetch or delete User A's media asset."""
    img_a = create_test_image("JPEG", 100, 100)
    created = await media_service.upload_media(
        mongo_test_db, db_session, user_a,
        UploadFile(file=io.BytesIO(img_a), filename="private.jpg", headers={"content-type": "image/jpeg"})
    )
    media_id = created["media_id"]

    # Unauthorized fetch
    with pytest.raises(HTTPException) as exc_info:
        await media_service.get_media_by_id(mongo_test_db, db_session, user_b, media_id)
    assert exc_info.value.status_code == 403

    # Unauthorized deletion
    with pytest.raises(HTTPException) as exc_info:
        await media_service.delete_media(mongo_test_db, db_session, user_b, media_id)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_q_successful_deletion_removes_both_doc_and_binary(media_service, mongo_test_db, db_session, user_a, temp_upload_dir):
    """Test Q: Deleting media removes MongoDB metadata and deletes physical file from storage."""
    img_a = create_test_image("JPEG", 100, 100)
    created = await media_service.upload_media(
        mongo_test_db, db_session, user_a,
        UploadFile(file=io.BytesIO(img_a), filename="delete_me.jpg", headers={"content-type": "image/jpeg"})
    )
    media_id = created["media_id"]
    storage_path = created["storage_path"]
    full_disk_path = os.path.join(temp_upload_dir, storage_path)

    assert os.path.isfile(full_disk_path)

    # Perform deletion
    deleted = await media_service.delete_media(mongo_test_db, db_session, user_a, media_id)
    assert deleted is True

    # Verify physical file is gone
    assert not os.path.exists(full_disk_path)

    # Verify MongoDB doc is gone
    with pytest.raises(HTTPException) as exc_info:
        await media_service.get_media_by_id(mongo_test_db, db_session, user_a, media_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_s_mongodb_failure_rolls_back_storage_file(local_storage, user_a, db_session, temp_upload_dir):
    """Test S: If MongoDB insert fails, storage binary is automatically rolled back and deleted."""
    # Create mock mongo database that fails on insert
    class FailingMongoCollection:
        async def insert_one(self, doc):
            raise RuntimeError("Simulated MongoDB write error")

    class FailingMongoDB(dict):
        def __getitem__(self, item):
            return FailingMongoCollection()

    failing_db = FailingMongoDB()
    svc = MediaService(storage_service=local_storage)

    img_bytes = create_test_image("JPEG", 100, 100)
    upload_file = UploadFile(
        file=io.BytesIO(img_bytes),
        filename="rollback_test.jpg",
        headers={"content-type": "image/jpeg"}
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.upload_media(failing_db, db_session, user_a, upload_file)
    assert exc_info.value.status_code == 500

    # Ensure no orphaned files remain in temp directory
    files_in_dir = []
    for root, _, files in os.walk(temp_upload_dir):
        for f in files:
            files_in_dir.append(os.path.join(root, f))
    assert len(files_in_dir) == 0


def test_t_path_traversal_protection(local_storage):
    """Test T: Path traversal sequences are detected and rejected by LocalStorageService."""
    with pytest.raises(HTTPException) as exc_info:
        local_storage._resolve_safe_path("../../../windows/system32/cmd.exe")
    assert exc_info.value.status_code == 400
    assert "Path traversal attempt detected" in exc_info.value.detail

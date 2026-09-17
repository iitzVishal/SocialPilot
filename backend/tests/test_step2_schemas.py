import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from app.models.enums import SocialPlatform, PostStatus, PublishResultStatus
from app.schemas.media import MediaAttachment, MediaAssetCreate, MediaAssetResponse
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostScheduleRequest,
    PostResponse,
    PlatformCustomization,
    AccountPublishResult,
)


def test_1_valid_post_create():
    """Verify creating a valid draft post with base content and target platforms."""
    payload = {
        "title": "Spring Launch Post",
        "base_content": "Excited to launch our new product line!",
        "target_platforms": ["facebook", "twitter"],
        "target_accounts": [1, 2],
        "team_id": None,
    }
    post = PostCreate(**payload)
    assert post.title == "Spring Launch Post"
    assert post.base_content == "Excited to launch our new product line!"
    assert post.target_platforms == [SocialPlatform.FACEBOOK, SocialPlatform.TWITTER]
    assert post.target_accounts == [1, 2]
    assert post.publish_now is False
    assert post.scheduled_at is None


def test_2_invalid_platform_in_post_create():
    """Verify rejection when target_platforms contains an unsupported platform string."""
    payload = {
        "base_content": "Hello World",
        "target_platforms": ["myspace", "facebook"],
    }
    with pytest.raises(ValidationError) as exc_info:
        PostCreate(**payload)
    assert "target_platforms" in str(exc_info.value)


def test_3_invalid_status_enum():
    """Verify rejection when an invalid post status string is passed."""
    with pytest.raises(ValueError):
        PostStatus("in_progress")  # Not in PostStatus enum


def test_4_invalid_scheduling_timestamp_in_past():
    """Verify scheduled_at in the past is rejected."""
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {
        "base_content": "Scheduled Post",
        "target_accounts": [1],
        "scheduled_at": past_time,
    }
    with pytest.raises(ValidationError) as exc_info:
        PostCreate(**payload)
    assert "Scheduled timestamp must be in the future" in str(exc_info.value)


def test_5_empty_target_accounts_on_scheduling_or_publishing():
    """Verify scheduling or immediate publishing requires target_accounts."""
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
    
    # 5a. Scheduled post with empty accounts list
    with pytest.raises(ValidationError) as exc_info:
        PostCreate(
            base_content="Scheduled without accounts",
            target_accounts=[],
            scheduled_at=future_time,
        )
    assert "Target accounts must be selected" in str(exc_info.value)

    # 5b. Publish now with empty accounts list
    with pytest.raises(ValidationError) as exc_info:
        PostCreate(
            base_content="Publish now without accounts",
            target_accounts=[],
            publish_now=True,
        )
    assert "Target accounts must be selected" in str(exc_info.value)


def test_6_valid_media_metadata():
    """Verify valid media attachment and media asset models."""
    attachment = MediaAttachment(
        media_id="media-uuid-1234",
        url="/uploads/media/2026/08/hero.jpg",
        file_name="hero.jpg",
        file_type="image/jpeg",
        file_size=204800,
        width=1200,
        height=630,
        aspect_ratio="1.91:1",
        alt_text="Banner hero image",
    )
    assert attachment.media_id == "media-uuid-1234"
    assert attachment.width == 1200
    assert attachment.height == 630
    assert attachment.file_size == 204800


def test_7_invalid_negative_file_size():
    """Verify rejection of negative media file sizes."""
    with pytest.raises(ValidationError) as exc_info:
        MediaAttachment(
            media_id="media-uuid-1234",
            url="/uploads/hero.jpg",
            file_name="hero.jpg",
            file_type="image/jpeg",
            file_size=-500,
        )
    assert "greater than or equal to 0" in str(exc_info.value)


def test_8_invalid_dimensions():
    """Verify rejection when width or height is <= 0."""
    with pytest.raises(ValidationError) as exc_info:
        MediaAttachment(
            media_id="media-uuid-1234",
            url="/uploads/hero.jpg",
            file_name="hero.jpg",
            file_type="image/jpeg",
            file_size=1000,
            width=0,  # Invalid
        )
    assert "greater than 0" in str(exc_info.value)


def test_9_valid_platform_customization():
    """Verify platform customizations dictionary with valid platform keys."""
    customizations = {
        "twitter": PlatformCustomization(content="Custom short text for X"),
        "instagram": PlatformCustomization(content="Instagram caption with hashtags", aspect_ratio_override="1:1"),
    }
    post = PostCreate(
        base_content="Default base content",
        platform_customizations=customizations,
    )
    assert post.platform_customizations["twitter"].content == "Custom short text for X"
    assert post.platform_customizations["instagram"].aspect_ratio_override == "1:1"

    # Test invalid customization key
    with pytest.raises(ValidationError) as exc_info:
        PostCreate(
            base_content="Default base content",
            platform_customizations={"tiktok": PlatformCustomization(content="Invalid key")},
        )
    assert "Invalid platform customization key" in str(exc_info.value)


def test_10_valid_publish_result():
    """Verify per-account publish result structure."""
    result = AccountPublishResult(
        account_id=10,
        platform=SocialPlatform.FACEBOOK,
        status=PublishResultStatus.SUCCESS,
        external_post_id="fb_post_987654321",
        published_at=datetime.now(timezone.utc),
        attempt_count=1,
    )
    assert result.account_id == 10
    assert result.status == PublishResultStatus.SUCCESS
    assert result.external_post_id == "fb_post_987654321"
    assert result.error_code is None


def test_11_invalid_publish_result_status():
    """Verify rejection of invalid publish result status string."""
    with pytest.raises(ValidationError) as exc_info:
        AccountPublishResult(
            account_id=10,
            platform=SocialPlatform.TWITTER,
            status="completed",  # Invalid (must be PublishResultStatus)
        )
    assert "status" in str(exc_info.value)

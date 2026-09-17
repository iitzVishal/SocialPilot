import pytest
from fastapi import HTTPException

from app.models.enums import SocialPlatform, PublishResultStatus, SocialAccountStatus
from app.models.social_account import SocialAccount
from app.services.adapters.base import BasePlatformAdapter, ValidationResult, AdapterPublishResult
from app.services.adapters import (
    get_platform_adapter,
    FacebookAdapter,
    InstagramAdapter,
    LinkedInAdapter,
    TwitterAdapter,
    YouTubeAdapter,
    PinterestAdapter,
)


# Test-only deterministic adapter (strictly contained in tests)
class TestDeterministicAdapter(BasePlatformAdapter):
    platform = SocialPlatform.TWITTER

    def validate_content(self, content: str, media: list, customization=None) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def format_payload(self, content: str, media: list, customization=None) -> dict:
        return {"text": content}

    async def publish(self, social_account: SocialAccount, payload: dict) -> AdapterPublishResult:
        return AdapterPublishResult(
            platform=self.platform,
            status=PublishResultStatus.SUCCESS,
            external_post_id="test_mock_12345",
            retryable=False
        )


@pytest.fixture
def mock_social_account():
    return SocialAccount(
        id=1,
        user_id=1,
        platform=SocialPlatform.TWITTER,
        account_name="Official Feed",
        account_identifier="tw_123",
        access_token="secret_encrypted_token",
        connection_status=SocialAccountStatus.CONNECTED,
    )


def test_1_and_2_adapter_registry_and_interface():
    """Test 1 & 2: Factory resolves all 6 platforms and all implement BasePlatformAdapter."""
    platforms = [
        SocialPlatform.FACEBOOK,
        SocialPlatform.INSTAGRAM,
        SocialPlatform.LINKEDIN,
        SocialPlatform.TWITTER,
        SocialPlatform.YOUTUBE,
        SocialPlatform.PINTEREST,
    ]
    for p in platforms:
        adapter = get_platform_adapter(p)
        assert isinstance(adapter, BasePlatformAdapter)
        assert adapter.platform == p

    # Test string resolution
    assert isinstance(get_platform_adapter("facebook"), FacebookAdapter)
    assert isinstance(get_platform_adapter("twitter"), TwitterAdapter)


def test_3_twitter_char_limit_rejection():
    """Test 3: Content > 280 characters is rejected by Twitter adapter."""
    adapter = TwitterAdapter()
    long_tweet = "A" * 281
    res = adapter.validate_content(content=long_tweet, media=[])
    assert res.is_valid is False
    assert any("exceeds 280 characters" in e for e in res.errors)


def test_4_valid_twitter_content_passes():
    """Test 4: Valid content under 280 chars passes."""
    adapter = TwitterAdapter()
    valid_tweet = "Launching our brand new product today! #excited"
    res = adapter.validate_content(content=valid_tweet, media=[])
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_5_twitter_media_validation():
    """Test 5: Twitter rejects >4 images or mixing video + image."""
    adapter = TwitterAdapter()
    images = [{"media_id": f"img_{i}", "file_type": "image/jpeg"} for i in range(5)]
    res = adapter.validate_content(content="5 images test", media=images)
    assert res.is_valid is False
    assert any("maximum of 4 images" in e for e in res.errors)

    # Mixing video and image
    mixed = [
        {"media_id": "vid_1", "file_type": "video/mp4"},
        {"media_id": "img_1", "file_type": "image/jpeg"},
    ]
    res_mixed = adapter.validate_content(content="mixed media", media=mixed)
    assert res_mixed.is_valid is False
    assert any("mixing images and video" in e for e in res_mixed.errors)


def test_6_instagram_media_requirement():
    """Test 6: Instagram rejects text-only posts (requires at least 1 photo/video)."""
    adapter = InstagramAdapter()
    res_no_media = adapter.validate_content(content="Caption only without photo", media=[])
    assert res_no_media.is_valid is False
    assert any("requires at least 1 media attachment" in e for e in res_no_media.errors)

    # With media, it passes
    media = [{"media_id": "img_1", "url": "/uploads/img.jpg", "file_type": "image/jpeg"}]
    res_with_media = adapter.validate_content(content="Great photo!", media=media)
    assert res_with_media.is_valid is True


def test_7_youtube_video_and_title_requirement():
    """Test 7: YouTube rejects publishing without video attachment or missing title."""
    adapter = YouTubeAdapter()

    # 7a. No video
    res1 = adapter.validate_content(content="Description", media=[])
    assert res1.is_valid is False
    assert any("requires at least 1 video attachment" in e for e in res1.errors)

    # 7b. Video provided but no title
    video_media = [{"media_id": "vid_1", "file_type": "video/mp4", "url": "/uploads/vid.mp4"}]
    res2 = adapter.validate_content(content="Description", media=video_media, customization={"title": ""})
    assert res2.is_valid is False
    assert any("requires a non-empty video title" in e for e in res2.errors)

    # 7c. Video + title passes
    res3 = adapter.validate_content(content="Description", media=video_media, customization={"title": "My Vlog #1"})
    assert res3.is_valid is True


def test_8_pinterest_board_and_image_requirement():
    """Test 8: Pinterest requires image and destination board identifier."""
    adapter = PinterestAdapter()

    # 8a. No image
    res1 = adapter.validate_content(content="Pin text", media=[], customization={"destination_board": "board_1"})
    assert res1.is_valid is False
    assert any("requires at least 1 image or video" in e for e in res1.errors)

    # 8b. Image but no board
    img_media = [{"media_id": "pin_img", "file_type": "image/jpeg", "url": "/uploads/pin.jpg"}]
    res2 = adapter.validate_content(content="Pin text", media=img_media, customization={"destination_board": ""})
    assert res2.is_valid is False
    assert any("requires a destination board identifier" in e for e in res2.errors)

    # 8c. Image + board passes
    res3 = adapter.validate_content(content="Pin text", media=img_media, customization={"destination_board": "home_decor"})
    assert res3.is_valid is True


def test_9_invalid_platform_resolution():
    """Test 9: Invalid platform string raises HTTP 400."""
    with pytest.raises(HTTPException) as exc_info:
        get_platform_adapter("tiktok_unsupported")
    assert exc_info.value.status_code == 400
    assert "Unsupported social platform" in exc_info.value.detail


@pytest.mark.asyncio
async def test_10_11_12_zero_fake_publishing_guarantee(mock_social_account):
    """
    Test 10, 11, 12: Production adapters MUST return NOT_CONFIGURED, status PENDING_EXTERNAL_INTEGRATION,
    external_post_id None, and NEVER report fake success.
    """
    adapters = [
        FacebookAdapter(),
        InstagramAdapter(),
        LinkedInAdapter(),
        TwitterAdapter(),
        YouTubeAdapter(),
        PinterestAdapter(),
    ]

    for adapter in adapters:
        payload = adapter.format_payload(content="Sample text", media=[])
        result = await adapter.publish(social_account=mock_social_account, payload=payload)

        # Zero fake publishing assertions
        assert result.status == PublishResultStatus.PENDING_EXTERNAL_INTEGRATION
        assert result.error_code == "NOT_CONFIGURED"
        assert result.external_post_id is None
        assert result.status != PublishResultStatus.SUCCESS
        assert result.published_at is None
        assert "not configured" in result.error_message.lower()


def test_13_test_adapter_remains_isolated():
    """Test 13: Test-only adapter is isolated and functional within test scope."""
    test_adapter = TestDeterministicAdapter()
    assert test_adapter.platform == SocialPlatform.TWITTER
    res = test_adapter.validate_content("anything", [])
    assert res.is_valid is True


@pytest.mark.asyncio
async def test_14_credentials_not_leaked_in_errors_or_logs(mock_social_account):
    """Test 14: Secret credentials are never leaked in AdapterPublishResult error strings."""
    adapter = TwitterAdapter()
    payload = adapter.format_payload(content="Test", media=[])
    result = await adapter.publish(social_account=mock_social_account, payload=payload)

    # Ensure secret_encrypted_token is not inside error message
    assert "secret_encrypted_token" not in str(result.error_message)
    assert "secret" not in str(result.error_message).lower()

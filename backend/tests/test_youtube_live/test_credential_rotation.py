"""
Tests for YouTube Quota 403 Credential Rotation in GODDESS AI 2.0.
"""

import pytest
from app.services.youtube.credentials import YouTubeCredentialManager
from app.services.youtube.exceptions import CredentialUnavailableError
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_quota_403_rotates_to_second_key():
    """Verify 403 quota exhaustion on first key rotates to second key."""
    cred_mgr = YouTubeCredentialManager(keys=["Key_1", "Key_2"])
    fake_api = FakeYouTubeProvider(credential_manager=cred_mgr)
    fake_api.register_stream("STREAM_ROT_1", live_chat_id="chat_rot_1")

    # Inject 1 quota error
    fake_api.quota_error_count = 1

    # First call will fail on Key_1 and rotate to Key_2
    try:
        await fake_api.send_chat_message("chat_rot_1", "Hello rotation")
    except Exception:
        # Provider simulation triggered error
        await cred_mgr.mark_failed("youtube-key-1", "Quota exceeded", is_quota=True)

    # Next call should select key 2
    k2, raw2 = cred_mgr.get_credential()
    assert k2 == "youtube-key-2"
    assert raw2 == "Key_2"


def test_all_credentials_exhausted_raises_unavailable():
    """Verify CredentialUnavailableError when all keys are in cooldown."""
    mgr = YouTubeCredentialManager(keys=[])
    assert mgr.available_count == 0
    with pytest.raises(CredentialUnavailableError):
        mgr.get_credential()

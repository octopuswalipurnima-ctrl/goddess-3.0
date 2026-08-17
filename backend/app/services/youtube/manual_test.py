"""
Controlled Real YouTube Live API Manual Test Harness for GODDESS AI 2.0.

Provides an operator-gated, safe testing script for connecting to real YouTube Live streams.
Will ONLY run if explicitly enabled via environment variable `RUN_REAL_YOUTUBE_TEST=true`.
Never executes automatically during unit tests or production startup.
"""

import asyncio
import os
import sys

from app.core.config import settings
from app.core.logging import get_logger
from app.services.youtube.client import youtube_client
from app.services.youtube.stream_session import StreamSession

logger = get_logger("youtube.manual_test")


async def run_controlled_live_test(stream_id: str, allow_chat_send: bool = False) -> None:
    """
    Executes a controlled live stream connection test against a private/unlisted stream.
    """
    if os.getenv("RUN_REAL_YOUTUBE_TEST", "").lower() not in ("true", "1"):
        logger.warning(
            "Controlled Real YouTube Live test skipped: RUN_REAL_YOUTUBE_TEST is not set to 'true'. "
            "To run a real test against a private/unlisted stream, set RUN_REAL_YOUTUBE_TEST=true."
        )
        return

    logger.info(f"Starting controlled live stream test for stream_id: {stream_id}")

    # 1. Verify credentials configured
    if not settings.youtube_api_keys:
        logger.error("No YouTube API keys configured in environment.")
        return

    # 2. Initialize and start session
    session = StreamSession(stream_id=stream_id, api_client=youtube_client)
    try:
        await session.start()
        logger.info(
            f"Session started successfully. Title='{session.stream_info.title if session.stream_info else 'N/A'}', "
            f"Chat ID='{session.stream_info.live_chat_id if session.stream_info else 'N/A'}'"
        )

        # 3. Listen for incoming chat messages for 10 seconds
        logger.info("Listening for incoming chat messages for 10 seconds...")
        await asyncio.sleep(10.0)

        # 4. Optionally test sending a message if explicitly allowed
        if allow_chat_send and session.stream_info and session.stream_info.live_chat_id:
            logger.info("Sending controlled test ping message to live chat...")
            sent = await session.send_chat_message("[GODDESS AI 2.0] Controlled test ping — all systems nominal.")
            logger.info(f"Test message posted: id={sent.message_id}")

        summary = session.to_summary()
        logger.info(f"Session Summary: {summary.model_dump_json(indent=2)}")

    finally:
        await session.stop(reason="Controlled test complete")
        logger.info("Controlled live stream test completed gracefully.")


if __name__ == "__main__":
    test_stream = os.getenv("TEST_YOUTUBE_STREAM_ID", "")
    if not test_stream:
        print("Usage: RUN_REAL_YOUTUBE_TEST=true TEST_YOUTUBE_STREAM_ID=<id> python manual_test.py")
        sys.exit(0)

    asyncio.run(run_controlled_live_test(test_stream, allow_chat_send=os.getenv("SEND_TEST_MESSAGE", "").lower() == "true"))

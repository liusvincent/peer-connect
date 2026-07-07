""" Unit test for webrtc

Test plan:

WebRTCSession init
- Verify it creates the required objects
- Verify session starts with open state
- Verify session does not start worker thread yet

WebRTCSession close
- Verify close() is idempotent (safe to call multiple times).
- Verify the stop event is set.
- Verify the video track is stopped.
- Verify the peer connection is closed.
- Verify the worker thread is joined if running.
"""

import pytest
from webrtc import WebRTCSession, StreamConfig
from unittest import mock

def test_webrtc_init():
    config = StreamConfig()
    on_coordinates = mock.Mock()
    session = WebRTCSession(config, on_coordinates)

    assert session.config is config
    assert session.on_coordinates is on_coordinates
    assert session.worker is None
    assert session.closed is False
    assert session.frame_queue.maxsize == 3
    assert not session.stop_event.is_set()
    assert session.track is not None

@pytest.mark.asyncio
async def test_close_stops_session():
    config = StreamConfig()
    on_coordinates = mock.Mock()
    session = WebRTCSession(config, on_coordinates)
    session.track.stop = mock.Mock()
    session.pc.close = mock.AsyncMock()
    await session.close()

    assert session.closed is True
    assert session.stop_event.is_set()
    session.track.stop.assert_called_once()
    session.pc.close.assert_called_once()

@pytest.mark.asyncio
async def test_close_is_idempotent():
    config = StreamConfig()
    on_coordinates = mock.Mock()
    session = WebRTCSession(config, on_coordinates)
    session.track.stop = mock.Mock()
    session.pc.close = mock.AsyncMock()
    await session.close()
    await session.close()
    
    session.track.stop.assert_called_once()
    session.pc.close.assert_called_once()
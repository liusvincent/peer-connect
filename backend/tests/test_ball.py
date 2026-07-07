""" Unit test for ball.py

Test plan:

BallVideoTrack 
- Verify recv() returns an AV VideoFrame
- Verify frame_data is read from frame_queue
- Veify pts and time_base are assigned correctly

ball_worker
- Verify frames are generated with the expected dimensions and type.
- Verify generated frames are added to the frame queue.
- Verify on_coordinates() is called with the ball's position.
- Verify the worker removes old frames when the queue is full.
- Verify the worker exits cleanly when stop_event is set.
- Verify the ball bounces correctly when reaching the frame boundaries.
- Verify the worker respects the configured frame rate.
"""

import pytest
import queue
import numpy as np
from ball import ball_worker, BallVideoTrack
from fractions import Fraction
from av import VideoFrame

@pytest.mark.asyncio
async def test_recv(monkeypatch: pytest.MonkeyPatch):
    frame_queue = queue.Queue()
    expected_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    expected_frame[100, 200] = [0, 0, 255]
    frame_queue.put(expected_frame)
    track = BallVideoTrack(frame_queue)
    
    async def fake_next_timestamp():
        return 123, Fraction(1, 90000)
    
    monkeypatch.setattr(track, "next_timestamp", fake_next_timestamp)
    video_frame = await track.recv()
    
    assert isinstance(video_frame, VideoFrame)
    assert video_frame.pts == 123
    assert video_frame.time_base == Fraction(1, 90000)
    actual_frame = video_frame.to_ndarray(format="bgr24")
    assert np.array_equal(actual_frame, expected_frame)
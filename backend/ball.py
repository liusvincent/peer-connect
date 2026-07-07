import cv2
import numpy as np
import threading
import queue
import time

import asyncio

from aiortc.mediastreams import VideoStreamTrack
from av import VideoFrame

from typing import Callable


class BallVideoTrack(VideoStreamTrack):
    def __init__(self, frame_queue: queue.Queue):
        super().__init__()
        self.frame_queue = frame_queue

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()

        frame_array = await asyncio.to_thread(self.frame_queue.get)

        video_frame = VideoFrame.from_ndarray(frame_array, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

def ball_worker(
    frame_queue: queue.Queue,
    stop_event: threading.Event,
    config,
    on_coordinates: Callable[[int, int], None],
):
    x, y = 320, 240
    vx, vy = 4, 3
    radius = 20

    width, height = 640, 480

    while not stop_event.is_set():
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        if x - radius <= 0 or x + radius >= width:
            vx *= -1
        if y - radius <= 0 or y + radius >= height:
            vy *= -1
        x += vx
        y += vy
        cv2.circle(frame, (x, y), radius, (0, 0, 255), -1)
        if frame_queue.full():
            frame_queue.get_nowait()
        frame_queue.put_nowait(frame)
        on_coordinates(x, y)
        time.sleep(1 / config.fps)  # fps

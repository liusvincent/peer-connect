# Backend: Server

## Overview

The [backend](../backend) repository focuses on the server implementation. It is written in Python.

The directory structure is as follows:
```text
backend/
├-─ main.py          main thing
├── meeting.py       Coordinates a participant's meeting session
├── messages.py      Defines and validates the signaling protocol
├── rooms.py         Manages rooms, participants, lobbies, and media routing
├── webrtc.py        Manages a participant's server-side WebRTC connection
└── webtransport.py  Accepts WebTransport sessions and dispatches messages
```


# Peer-Connect 

### Try out the app -> https://peer-connect-weld.vercel.app/

A pet project to learn about servers. Peer-Connect is a full-stack video calling web application inspired by Google Meet. This project was built to explore how real-time communication servers work and to practice system design through the implementation of an SFU (Selective Forwarding Unit) server.

### Built With
**Frontend**
- React
- Vite
- Tailwind CSS

**Backend**
- Python

**Key Libraries**
- [aiortc](https://github.com/aiortc/aiortc) — WebRTC implementation
- [aioquic](https://github.com/aiortc/aioquic) — QUIC and WebTransport implementation

## Getting Started

### Prerequisites
What you need to run this project:
- [Node.js](https://nodejs.org/) — v20 or later
- [Python](https://www.python.org/) — v3.11 or later
- [OpenSSL](https://www.openssl.org/) — required for generating certificates/keys

## Development

### Setup

1. Clone or fork the repository
```bash
git clone https://github.com/liusvincent/peer-connect.git
```

2. Go to the project directory
```bash
cd peer-connect
```

3. Install the frontend dependencies
```bash
cd frontend
npm install
```

4. Install the backend dependencies.
```bash
cd ../backend
python -m venv .venv
```

Activate the virtual environment:
macOS/Linux
```bash
source .venv/bin/activate
```
Windows
```bash
.venv\Scripts\activate
```

Then install the Python dependencies:
```bash
pip install -r requirements.txt
```

5. Generate a local TLS certificate
```bash
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
  -keyout key.pem -out cert.pem \
  -days 13 -nodes \
  -subj "/CN=localhost"
```

Then generate the SHA-256 fingerprint:
```bash
openssl x509 -in cert.pem -outform DER | openssl dgst -sha256 | awk '{print toupper($2)}'
```

Paste the output into [frontend/src/services/webtransport.ts](frontend/src/services/webtransport.ts)

> [!NOTE]
> The certificate's validity period must not exceed 14 days. Otherwise, the browser will reject the WebTransport connection during the handshake.

6. Start the backend server

From the backend directory:
```bash
python main.py
```

7. Start the frontend development server

Open another terminal and run:
```bash
cd frontend
npm run dev
```

8. Open the local development URL shown by Vite in your browser
`http://localhost:5173`

> [!NOTE]
> Because Peer-Connect uses WebRTC and WebTransport, your browser may require you to trust the locally generated certificate before a WebTransport connection can be established.

## Deployment

Peer-connect frontend is deployed on Vercel, and the backend is deployed on a Linux VM.

## Architecture

Peer-Connect uses an SFU server for multi-user video calls. Clients establish WebRTC connections with the SFU, which forwards media tracks between participants. WebTransport is used for communication between the client and server.

For a detailed explanation, see [`docs/architecture.md`](docs/architecture.md).

## Documentation

Additional documentation is available in the [`docs`](docs) directory. It covers the system design, architectural decisions, design patterns, and overall code structure of the project.

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.

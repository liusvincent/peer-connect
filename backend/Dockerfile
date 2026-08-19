FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PEER_CONNECT_HOST=0.0.0.0 \
    PEER_CONNECT_PORT=4433

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser *.py ./

USER appuser

EXPOSE 4433/udp

CMD ["python", "main.py"]
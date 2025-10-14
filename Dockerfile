FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \\
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt && \
    pip install gunicorn

# App code
COPY . /app

# Create runtime dirs (mounted as volumes in compose)
RUN mkdir -p /app/logs /app/files /app/files/pics

EXPOSE 5000

# Default env (override in container runtime)
ENV AUTH_FLOW=web \
    OAUTH_REDIRECT_URL=http://127.0.0.1:5000/oauth/google/callback

# Run with Gunicorn
CMD [ \
  "gunicorn", "-w", "2", "-k", "gthread", \
  "-t", "120", "--threads", "8", \
  "-b", "0.0.0.0:5000", "src.api_server:app" \
]


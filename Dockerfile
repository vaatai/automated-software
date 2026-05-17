# ---------------------------------------------------------------------------
# Backend (FastAPI + Celery workers) production image
# Multi-stage: install deps → install Playwright → copy app
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── dependency layer (cached unless requirements.txt changes) ──
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

# ── final image ────────────────────────────────────────────────
FROM base AS runtime

# Copy installed Python packages and Playwright browsers from deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY --from=deps /root/.cache/ms-playwright /root/.cache/ms-playwright

# Copy application code
COPY . .

# Create runtime directories
RUN mkdir -p screenshots static templates html_snapshots debug_reports browser_logs

# Non-root user for API (workers need root for Playwright)
RUN adduser --disabled-password --gecos "" appuser

EXPOSE 8000

# Default: run API server
# Override CMD for workers, beat, flower, etc.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

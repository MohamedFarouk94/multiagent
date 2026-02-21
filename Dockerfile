# ── Base image ──────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── OS-level dependencies ────────────────────────────────────────────────────
# Needed by some packages (cryptography, pycparser, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ──────────────────────────────────────────────
# Copy only requirements first to leverage Docker layer caching.
# If requirements.txt hasn't changed, this layer won't be rebuilt.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy project source ──────────────────────────────────────────────────────
COPY backend/ ./backend/

# ── Expose the application port ──────────────────────────────────────────────
EXPOSE 8000

# ── Default command ──────────────────────────────────────────────────────────
# NOTE: --reload is convenient in development but should be removed in production.
# Override this command in your production deployment.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

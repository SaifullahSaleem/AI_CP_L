# =============================================================================
# Dockerfile — Agentic Research Paper Assistant
# =============================================================================
# Base image:  python:3.12-slim
#   - Python 3.12 matches LangGraph/LangChain requirements
#   - 'slim' variant (~150 MB vs ~1 GB full) strips man pages, docs, dev headers
#   - Alpine rejected: grpcio (Firebase/Google) requires glibc; musl builds add
#     10+ min compile time and risk segfaults
#
# Layer strategy:
#   1. System deps          — rarely change  → cached aggressively
#   2. requirements.txt     — changes on dep updates only
#   3. pip install          — cached unless requirements.txt changes
#   4. Application source   — changes most often → invalidates fewest layers
#
# Multi-stage rationale:
#   Stage 1 (builder): installs build tools + compiles native extensions
#   Stage 2 (runtime): copies only the venv — no gcc, no pip cache, ~50% smaller
# =============================================================================

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install build dependencies for native extensions (grpcio, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Create virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies first (cache-friendly)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir redis


# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Labels
LABEL maintainer="research-paper-assistant"
LABEL description="Agentic Research Paper Assistant — FastAPI + LangGraph"

# Copy virtualenv from builder (no build tools in final image)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home appuser

# Set working directory
WORKDIR /app

# Copy application source code
COPY app/ ./app/
COPY agent/ ./agent/
COPY db/ ./db/
COPY services/ ./services/
COPY tools/ ./tools/
COPY utils/ ./utils/
COPY schemas/ ./schemas/

# Create secrets mount point
RUN mkdir -p /app/secrets && chown appuser:appuser /app/secrets

# Switch to non-root user
USER appuser

# Environment defaults (overridden at runtime via env_file / -e flags)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FIREBASE_CREDENTIALS_PATH=/app/secrets/firebase-credentials.json

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

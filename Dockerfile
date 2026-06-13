# ==========================================
# STAGE 1: Builder
# ==========================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable byte-code compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy configuration files and source code
COPY pyproject.toml README.md /app/
COPY src /app/src

# Create a virtualenv and install the project along with its dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    uv pip install .

# ==========================================
# STAGE 2: Final Runtime
# ==========================================
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the built virtualenv and application code from the builder stage
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV HOST=0.0.0.0
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Expose server port
EXPOSE 8000

# Execute server startup command
CMD ["uvicorn", "stock_predictor.main:app", "--host", "0.0.0.0", "--port", "8000"]

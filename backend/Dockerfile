FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_HTTP_TIMEOUT=120

WORKDIR /app

# Install uv
RUN pip install uv==0.4.29

FROM base AS deps
COPY pyproject.toml .
RUN uv pip install --system --no-cache -e ".[dev]"

FROM deps AS final
COPY . .
RUN chmod +x prestart.sh

# Run as non-root
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

ENTRYPOINT ["./prestart.sh"]

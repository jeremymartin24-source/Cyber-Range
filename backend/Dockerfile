FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install uv
RUN pip install uv==0.4.29

FROM base AS deps
COPY pyproject.toml .
RUN uv pip install --system --no-cache -e ".[dev]"

FROM deps AS final
COPY . .
RUN chmod +x prestart.sh
ENTRYPOINT ["./prestart.sh"]

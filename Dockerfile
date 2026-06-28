FROM python:3.14-slim

ARG VERSION=0.0.0
ARG COMMIT_SHA=unknown
ARG BUILD_DATE

LABEL org.opencontainers.image.title="InkTracker" \
      org.opencontainers.image.description="UV Print Cost Tracker — Self-hosted production and costing tracker" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${COMMIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.vendor="codebyit" \
      org.opencontainers.image.source="https://github.com/codebyit/inktracker" \
      org.opencontainers.image.url="https://github.com/codebyit/inktracker"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi \
    && npm run build:css \
    && npm run vendor:jsqr \
    && npm cache clean --force

RUN mkdir -p /app/static/uploads && chown -R app:app /app \
    && chmod +x /app/docker-entrypoint.sh

USER app

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Installation

## Quickest start (no clone)

Download the two files and start — the prebuilt image is pulled automatically:

```bash
curl -O https://raw.githubusercontent.com/codebyit/inktracker/main/docker-compose.public.yml
# saves the example straight to .env (required by Compose)
curl -o .env https://raw.githubusercontent.com/codebyit/inktracker/main/.env.example
docker compose -f docker-compose.public.yml up -d
```

Verify and open:

```bash
docker compose -f docker-compose.public.yml ps   # services should be running/healthy
```

Then visit **http://localhost:8000**.

## Profile A: All-in-one (app + postgres + redis)

1. Copy env:
   - `cp .env.example .env`
2. Start:
   - `docker compose -f docker-compose.public.yml up -d`
3. Open app:
   - `http://localhost:8000`

## Profile B: External PostgreSQL

1. Copy env:
   - `cp .env.example .env`
2. Set external `DATABASE_URL` in `.env`
3. Start:
   - `docker compose -f docker-compose.external-db.yml up -d`

## Container image

Both profiles run the prebuilt image `ghcr.io/codebyit/inktracker:latest`, pulled
automatically by `docker compose ... up -d` (no local build). To pin a version, set
`APP_IMAGE` in `.env`, e.g. `APP_IMAGE=ghcr.io/codebyit/inktracker:v0.9.0`. Tags:
`latest`, `vX.Y.Z`, `vX.Y.Z-<sha7>`.

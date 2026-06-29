# Installation

## Profile A: All-in-one (app + postgres + redis)

1. Copy env:
   - `cp .env.example .env`
2. Set a strong `SECRET_KEY` in `.env` (the default is `change-me`).
3. Start:
   - `docker compose -f docker-compose.public.yml up -d`
4. Open app:
   - `http://localhost:8000`

## Profile B: External PostgreSQL

1. Copy env:
   - `cp .env.example .env`
2. Set a strong `SECRET_KEY` and your external `DATABASE_URL` in `.env`
3. Start:
   - `docker compose -f docker-compose.external-db.yml up -d`

# Installation

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

# InkTrack

InkTrack is a self-hosted production and costing tracker for small print studios.

## Quick Start

1. Copy environment file:
   - `cp .env.example .env`
2. Start all services:
   - `docker compose -f docker-compose.public.yml up -d`
3. Open:
   - `http://localhost:8000`

Using an external PostgreSQL instead? See **Profile B** in
[`docs/installation.md`](docs/installation.md).

## Images

Public image is published to:
- `ghcr.io/codebyit/inktracker`

Recommended tags:
- `latest`
- `vX.Y.Z`
- `vX.Y.Z-<sha7>`

## Deployment Profiles

- `docker-compose.public.yml`: app + postgres + redis
- `docker-compose.external-db.yml`: app + redis (external postgres)

## Documentation

📘 **[User Manual](docs/README.md)** — end-user guide (dashboard, projects, analytics, settings).

Admin & install docs:

- `docs/installation.md`
- `docs/configuration.md`
- `docs/upgrading.md`
- `docs/troubleshooting.md`

## Security

Please read `SECURITY.md` before reporting vulnerabilities.

## License

This project is released under the GNU General Public License v3.0.

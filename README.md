# InkTrack

InkTrack is a self-hosted production and costing tracker for small print studios.

## Quick Start

No clone needed — grab the two files and start (uses the prebuilt image):

```bash
curl -O https://raw.githubusercontent.com/codebyit/inktracker/main/docker-compose.public.yml
curl -o .env https://raw.githubusercontent.com/codebyit/inktracker/main/.env.example
docker compose -f docker-compose.public.yml up -d
```

Then open **http://localhost:8000**.

Verify it's running:

```bash
docker compose -f docker-compose.public.yml ps   # all services "running"/"healthy"
```

Using an external PostgreSQL instead? See **Profile B** in
[`docs/installation.md`](docs/installation.md).

## Images

The Compose files run the prebuilt image — no local build needed. Both profiles
default to `ghcr.io/codebyit/inktracker:latest`; `docker compose ... up -d` pulls it
automatically. To pin a specific version, set `APP_IMAGE` in `.env`:

```dotenv
APP_IMAGE=ghcr.io/codebyit/inktracker:v0.9.0
```

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

# InkTrack

InkTrack is a self-hosted production and costing tracker for small print studios.

## Quick Start

No clone needed — grab the two files and start (uses the prebuilt image):

```bash
curl -O https://raw.githubusercontent.com/codebyit/inktracker/main/docker-compose.public.yml
# saves the example straight to .env (required by Compose)
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

### Update to the latest

```bash
docker compose -f docker-compose.public.yml pull
docker compose -f docker-compose.public.yml up -d
```

Migrations run automatically on start. See [`docs/upgrading.md`](docs/upgrading.md)
for pinning, rollback, and backup steps.

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

## Windows desktop app

Prefer a native app to Docker? InkTrack also ships as a standalone Windows
desktop build (the same FastAPI app in a local window — SQLite, no server). Grab
the installer or the portable ZIP from the [latest release](https://github.com/codebyit/inktracker/releases/latest).
Build details are in [`BUILD.md`](BUILD.md).

> Windows builds are code-signed by the [SignPath Foundation](https://signpath.org/).

## Security

Please read `SECURITY.md` before reporting vulnerabilities.

## Support

InkTrack is free and open source. If it's useful to your studio and you'd like to
support development, you can buy me a coffee:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/codebylt)

## License

This project is released under the GNU General Public License v3.0.

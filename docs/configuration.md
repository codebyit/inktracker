# Configuration

## Required

- `DATABASE_URL`

## Recommended

- `REDIS_URL`
- `APP_ENV`
- `APP_HOST`
- `APP_PORT`

## Optional admin auth

InkTracker runs without authentication by default (LAN-only / behind a VPN or tunnel).
To protect the destructive endpoints (`/settings/backup`, `/settings/restore`,
`/settings/reset`), set `ADMIN_API_TOKEN`. When set, those requests must include the
header `X-Admin-Token: <value>`. Leave it unset to keep the no-auth default.

Use a long random value, e.g. `openssl rand -hex 32`.

See `.env.example` for defaults.

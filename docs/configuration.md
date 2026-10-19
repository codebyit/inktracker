# Configuration

## Required

- `DATABASE_URL`

## Recommended

- `REDIS_URL`
- `APP_ENV`
- `APP_HOST`
- `APP_PORT`

## Environment variables with Compose

Both `docker-compose.public.yml` and `docker-compose.external-db.yml` explicitly
load `.env` into the app container through `env_file`. Put app settings in that
file beside the Compose file. Compose also uses `.env` for substitutions such as
`APP_IMAGE`; substitution alone does not inject arbitrary variables into a container.
Other deployment methods must explicitly supply the environment to the app process.

After changing `.env`, recreate the app container to load the new values (a restart
alone does not update its environment):

```bash
docker compose -f docker-compose.public.yml up -d --force-recreate app
```

For Profile B, use `-f docker-compose.external-db.yml` instead. Keep `.env` private;
do not share resolved environment output containing credentials or tokens.

## Local-development API documentation

`/docs`, `/redoc`, and `/openapi.json` are disabled by default. To enable the
interactive docs and schema for local development, add this to `.env`, then
recreate the app container as above:

```dotenv
ENABLE_API_DOCS=true
```

Remove the setting or set it to `false` and recreate the app container to disable
them again. This switch is **not authentication** and does not protect application
endpoints. Keep development API documentation private rather than exposing it publicly.

## Optional admin auth

InkTracker runs without authentication by default (LAN-only / behind a VPN or tunnel).
To protect the destructive endpoints (`/settings/backup`, `/settings/restore`,
`/settings/reset`), set `ADMIN_API_TOKEN`. When set, those requests must include the
header `X-Admin-Token: <value>`. Leave it unset to keep the no-auth default.

Use a long random value, e.g. `openssl rand -hex 32`.

See `.env.example` for defaults.

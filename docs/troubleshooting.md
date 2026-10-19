# Troubleshooting

## Container does not start

- Check logs: `docker compose -f docker-compose.public.yml logs app`
- Verify `.env` values
- If `.env` changed, [recreate the app container](configuration.md) to load it;
  restarting alone does not update the container environment. Profile B uses
  `-f docker-compose.external-db.yml` instead.

## Database errors

- Validate `DATABASE_URL`
- Check postgres readiness and credentials

### Unknown Alembic revision

In v0.16.1, a database revision absent from the image's migration tree stops startup
instead of being rewritten. This is a migration-history mismatch, not the same as
PostgreSQL being unready or rejecting credentials.

1. Preserve a database backup and capture app startup logs. Keep credentials and
   other sensitive values out of shared logs.
2. Check which image/tag is running, where the database originated, and whether its
   migration history belongs to that image's migration tree.
3. Seek a reviewed recovery path using the matching image/migrations, or restore
   a known-good backup with a compatible image. Preserve the current database first.

Do **not** delete `alembic_version`, blindly stamp a revision, or repeatedly restart
expecting history to be repaired. See [Upgrading](upgrading.md) for update/rollback
precautions. v0.16.1 adds no schema migrations, but older databases may still need
migrations from intervening releases.

## API documentation is unavailable

`/docs`, `/redoc`, and `/openapi.json` are intentionally disabled by default; this
alone does not indicate an app or database failure. For local development only,
use [the API-docs opt-in](configuration.md). If a protected admin request is rejected,
check its `X-Admin-Token` separately; enabling API docs does not bypass authentication.

## App not reachable

- Verify mapped port `8000:8000`
- Check host firewall

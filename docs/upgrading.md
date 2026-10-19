# Upgrading

## Update to the latest image

The container runs database migrations automatically on start. **v0.16.1 adds no
schema migrations**; this is specific to that release, not a guarantee for future
updates. Back up before updating and check the target release notes.

From the folder containing your `docker-compose.public.yml` and `.env`:

```bash
# 1. (Recommended) back up first — see Settings → Data for a DB backup,
#    and copy your Postgres/redis volumes if you keep them locally.

# 2. Pull the newest image
docker compose -f docker-compose.public.yml pull

# 3. Recreate the app container with the new image
docker compose -f docker-compose.public.yml up -d

# 4. Verify
docker compose -f docker-compose.public.yml ps      # services running/healthy
docker compose -f docker-compose.public.yml logs -f app   # watch migrations apply
```

Then reload **http://localhost:8000** and check the version in the sidebar footer.

### Pin to a specific version

By default the image is `:latest`. To control exactly which version you run, set
`APP_IMAGE` in `.env`, then re-run the pull/up steps:

```dotenv
APP_IMAGE=ghcr.io/codebyit/inktracker:v0.16.1
```

After pinning, `pull` fetches that tag and `up -d` switches to it. Updating later means
bumping the tag (or returning to `:latest`).

### Roll back

For example, `:v0.16.0` is the previous-release tag for a v0.16.1 update, **not an
unconditionally safe rollback**. Before changing `APP_IMAGE` and running pull +
`up -d`, confirm the older image supports the database's migration history and data.
If it does not, use a known-good pre-update backup with its matching image after
reviewing the release notes. Preserve the current database before attempting recovery.

### Migration-history failures

v0.16.1 preserves valid Alembic history and stops startup if the database references
a revision unknown to the image. Restarting does not rewrite that history.
Capture the logs and verify the image/database provenance and matching migration
tree. Do not delete or blindly stamp `alembic_version` to make startup pass.
Use the [migration troubleshooting guidance](troubleshooting.md) and obtain a reviewed
recovery path, or restore a known-good backup with a compatible image.

## Summary

1. Backup database and uploads
2. Pull new image tag
3. Recreate the container (migrations run automatically)
4. Validate app health and version

For major versions, read release notes first.

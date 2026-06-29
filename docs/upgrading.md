# Upgrading

## Update to the latest image

The container runs database migrations automatically on start, so updating is just
pull + recreate. From the folder containing your `docker-compose.public.yml` and `.env`:

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
APP_IMAGE=ghcr.io/codebyit/inktracker:v0.9.1
```

After pinning, `pull` fetches that tag and `up -d` switches to it. Updating later means
bumping the tag (or returning to `:latest`).

### Roll back

Set `APP_IMAGE` to the previous tag (e.g. `:v0.9.0`) and run pull + `up -d`. Restore your
database backup if a migration is not backward compatible (see release notes).

## Summary

1. Backup database and uploads
2. Pull new image tag
3. Recreate the container (migrations run automatically)
4. Validate app health and version

For major versions, read release notes first.

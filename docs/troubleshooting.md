# Troubleshooting

## Container does not start

- Check logs: `docker compose logs app`
- Verify `.env` values

## Database errors

- Validate `DATABASE_URL`
- Check postgres readiness and credentials

## App not reachable

- Verify mapped port `8000:8000`
- Check host firewall

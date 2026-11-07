# Secure Deployment Workflow

## Overview
The application now uses environment variables for sensitive configuration, ensuring secure deployment while maintaining easy local development.

## Local Development

1. **No special setup needed** - the app works out of the box with DEBUG enabled
   - Default SECRET_KEY for development only
   - DEBUG defaults to `True`
   - ALLOWED_HOSTS defaults to `localhost,127.0.0.1`

2. **Run locally:**
   ```bash
   python manage.py runserver
   ```

## Production Deployment

### One-time VPS Setup

1. **Generate a strong SECRET_KEY** on your VPS:
   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

2. **Create environment file** at `/home/deploy/DOCKER/plachtis/.env`, based on `.env.example`. Set at minimum:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_ALLOWED_HOSTS` (production hosts)

   For test deployment at `/home/deploy/DOCKER/plachtis-test`, copy the same template and use test values:
   - `CONTAINER_NAME=plachtis-test-web`
   - `DJANGO_ALLOWED_HOSTS=plachtis-test.remesh.cz`

3. **Keep `compose.yaml` next to `.env`.** The server copy is owned by the server, so CI does not update it. Changing it means re-running `bombur-onboard` from `ciakval/bombur-deploy`.

4. **Make `data/` writable by the container user (uid 1000):**
   ```bash
   sudo chown -R 1000:1000 /home/deploy/DOCKER/plachtis/data
   ```
   SQLite creates its journal next to the database, so the directory needs to be writable as well as `db.sqlite3`. Otherwise pages load but every write fails with a 500, including login. `python manage.py migrate` checks this at container start and fails with `SkaRe.E001` or `SkaRe.E002`.

### GitHub Secrets Setup

The only GitHub secret is `DEPLOY_SSH_KEY`, set as an environment secret on both the `production` and `test` environments. It lets CI ask for a deployment of one image and nothing else. Runtime secrets live in `.env` on the server.

### Automatic Deployment

- A push to `main` deploys to test (`plachtis-test.remesh.cz`).
- A `v*` tag deploys to production (`plachtis.remesh.cz`, `plachtis.skare.cz`).

In both cases GitHub Actions builds an image tagged with the Git commit SHA, pushes it to GitHub Container Registry and calls `bombur-deploy`, which pulls that image and runs `docker compose up -d`.

### Logs

```bash
ssh -p 10022 ciakval@bombur.remesh.cz
docker logs --since 24h plachtis-web
```

The output has the Gunicorn access log and Django's errors, including tracebacks for every 500.

## Caddy Configuration

The application uses whitenoise to serve static files directly from Django/Gunicorn. Your Caddy configuration should use a simple reverse proxy without special handling for static files:

```caddy
plachtis.remesh.cz {
    reverse_proxy plachtis-web:8000
}
```

**Important:** Do not configure Caddy to serve static files separately - whitenoise handles all static file serving with proper headers and compression.

## Static Files

### Development
- Static files are in `SkaRe/static/` (committed to Git)
- Django serves them automatically with DEBUG=True
- Run `python manage.py collectstatic` to test collection

### Production/Docker
- During Docker build, `collectstatic` runs automatically (see Dockerfile line 32)
- Static files are collected to `staticfiles/` directory (not committed to Git)
- Whitenoise serves them from memory with compression and caching headers
- Source files in `SkaRe/static/` must be committed to Git

**Important:** Always commit your source static files (`SkaRe/static/`) to Git. The `staticfiles/` directory is generated during deployment and should not be committed.

## Translations

### Development
- Translation source files (`.po`) are in `locale/` directory (committed to Git)
- Compiled translation files (`.mo`) are **not** committed to Git (excluded by `.gitignore`)
- Run `python manage.py compilemessages` to compile translations locally for testing

### Production/Docker
- During Docker build, `compilemessages` runs automatically after copying project files
- The `gettext` package is installed in the Docker image to enable compilation
- Compiled `.mo` files are generated at build time inside the container

**Important:** Only commit `.po` files (translation sources) to Git. The `.mo` files (compiled translations) are generated during deployment and should not be committed.

### Adding or Updating Translations
1. Update or create `.po` files in the `locale/` directory
2. Test locally: `python manage.py compilemessages` then `python manage.py runserver`
3. Commit only the `.po` files to Git
4. Deploy - the Docker build will automatically compile the translations

## Security Features

### Development (DEBUG=True)
- Uses default development SECRET_KEY
- No HTTPS enforcement
- Detailed error pages

### Production (DEBUG=False)
- Requires strong SECRET_KEY from environment
- HTTPS redirect enabled
- Secure cookies (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
- HSTS enabled (31536000 seconds = 1 year)
- XSS and content-type sniffing protection

## Important Security Notes

1. **Never commit .env files** - they're in .gitignore
2. **Rotate the SECRET_KEY** immediately (the old one was committed to git)
3. **Use strong random values** - minimum 50 characters
4. **Invalidate old sessions** after rotating SECRET_KEY (users need to log in again)

## Testing Deployment Settings

Check your production security before deploying:
```bash
python manage.py check --deploy
```

## Troubleshooting

If deployment fails:
1. Check GitHub Actions logs
2. Verify .env file exists on VPS
3. Ensure DJANGO_SECRET_KEY is set in VPS .env
4. Check docker logs: `docker logs plachtis-web`

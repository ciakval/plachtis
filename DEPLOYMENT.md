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

2. **Create environment file** at `/home/plachtis/DOCKER/plachtis/.env`:
   ```bash
   cd /home/plachtis/DOCKER/plachtis
   cat > .env << 'EOF'
   DJANGO_SECRET_KEY=<your-generated-secret-key-here>
   DJANGO_ALLOWED_HOSTS=plachtis.remesh.cz,plachtis.skare.cz
   EOF
   ```

3. **Update docker-compose.yml** to use the .env file:
   ```bash
   # The docker-compose.yml already references the variables
   # Just ensure your .env file exists in the same directory
   ```

### GitHub Secrets Setup

You need these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

- `VPS_HOST` - Your VPS IP or hostname
- `VPS_SSH_PORT` - SSH port (usually 22)
- `VPS_USER` - SSH username
- `VPS_SSH_KEY` - Private SSH key for authentication

### Automatic Deployment

Every push to `main` branch will:
1. Build a new Docker image
2. Push to GitHub Container Registry
3. Copy docker-compose.yml to VPS
4. Pull the new image on VPS
5. Restart containers with new code

## Caddy Configuration

The application uses whitenoise to serve static files directly from Django/Gunicorn. Your Caddy configuration should use a simple reverse proxy without special handling for static files:

```caddy
plachtis.remesh.cz {
    reverse_proxy localhost:8000
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

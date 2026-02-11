# Deployed web & Server Maintenance

This document explains how to perform manual maintenance steps.

Regularly, PlachtIS is deployed to the server through Github Actions, see [the deployment file](../.github/workflows/deploy.yml).

## Preparation

1. Get your SSH key enrolled

2. Log in to the server Bombur
    ```sh
    ssh -l plachtis -p 10022 bombur.remesh.cz
    # OR
    ssh plachtis@bombur.remesh.cz:10022
    ```
3. Go to the _DOCKER/plachtis_ directory
    ```sh
    cd DOCKER/plachtis
    ```


## Steps to perform

### Full reset

```sh
# In the DOCKER/plachtis directory
docker compose down
rm data/db.sqlite3
docker compose up --detach
docker exec -ti plachtis-web bash

# In the Docker container shell started by previous command
python manage.py createsuperuser

# Terminate Docker shell by Ctrl+C

# Logout from server by Ctrl+C
```

### Individual steps

#### Web shutdown

1. `docker compose down`.

#### Web startup

1. `docker compose up --detach`

#### Database reset (or backup)

1. Shut the web down
2. Delete (or move elsewhere) file _data/db.sqlite3_
    ```sh
    rm data/db.sqlite3
    # OR
    mv data/db.sqlite3 data/db.sqlite3-$(date --iso=seconds)
    ```

#### Create super-user account

Creating a superuser is needed in order to grant other users admin (staff) privileges and access to the Admin panel.

1. Make sure the web is running
2. Start a shell in the web container
   ```sh
   docker exec -ti plachtis-web bash
   ```
3. Create super-user using regular Django commands
    ```sh
    python manage.py createsuperuser
    ```

The superuser is saved to the database, so this must be done after database reset.

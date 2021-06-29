# Development

## Develop with Docker
Develop with simple configuration

### Backend

If setting up for the first time, follow instructions in [README](README.md).

*Note:* all commands may need to be run as root

Otherwise
1. Run `docker-compose run --rm django ./manage.py reset_db`
2. Follow **Initial Setup** section in [README](README.md) (i.e. `migrate` and `createsuperuser`).

#### Importing Data
(Note: it might be prudent to run the previous steps before this, i.e. `reset_db`, `migrate`, and `createsuperuser`)
1. Place folder containing sample data at root of project.
   - This folder will be referenced here as `sample_data` but can be arbitrarily named.
   - *NOTE:* `sample_data` should contain a CSV (referenced here as `file.csv`) with all paths prefixed by `/opt/django-project/`
2. Run `docker-compose build`
3. Finally, run `docker-compose run --rm  django python manage.py populate /opt/django-project/sample_data/file.csv`. This will create the corresponding models in the database.
   - *NOTE:* Ensure that correct filenames/paths are used.


## Frontend

After completing the steps for the backend, use the following instructions to start the frontend. The current frontend repo is located at `https://github.com/OpenImaging/miqa-web`

1. Clone and navigate to the `client` folder in the frontend repo. Run `npm run serve`
2. Start up the backend `docker-compose up`
3. Navigate to `http://localhost:8000/admin` and login using the credentials you used in `createsuperuser`
4. Using the admin interface, create an Application (located under section **DJANGO OAUTH TOOLKIT**) using the following parameters
    1. Client id: Set this to the value of `VUE_APP_OAUTH_CLIENT_ID` located in the `.env` file in frontend repo
    2. User: Click magnifying glass and select yourself
    3. Redirect uris: The uri of the frontend printed as a result of running step 1 (`npm run serve`). For example, `http://localhost:8081/`
    4. Client type: public
    5. Authorization grant type: Authorization Code
    6. Name: Any name will suffice
5. Finally, navigate to the frontend (again for example: `http://localhost:8081/`) and follow the login flow

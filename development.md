# Development

## Develop with Docker
Develop with simple configuration

### Backend

If setting up for the first time, follow instructions in [README](README.md).

*Note:* docker commands may need to be run as root

Otherwise
1. Run `docker-compose run --rm django ./manage.py reset_db`
2. Follow **Initial Setup** section in [README](README.md) (i.e. `migrate` and `createsuperuser`).

#### Importing Data
(Note: it might be prudent to run the previous steps before this, i.e. `reset_db`, `migrate`, and `createsuperuser`)
1. To import the sample data, set the import CSV to `/srv/samples/scans_to_review-2019-01-23.csv` in the GUI and click the Import button.
   If you have not set up the initial project yet, this can be done with `docker-compose run --rm  django python manage.py populate --csv /srv/samples/scans_to_review-2019-01-23.csv`.
2. To import other data, set the `SAMPLES_DIR` environment variable in your shell prior to running `docker-compose up`.
   The `SAMPLES_DIR` should contain your import CSV and all of the data to be imported.
   docker-compose will mount that directory at the same path (`${SAMPLES_DIR}:${SAMPLES_DIR}`), so your import CSV can use the same paths as on your native file system.


## Frontend

After completing the steps for the backend, use the following instructions to start the frontend. The codebase for the frontend is located in the `client` folder.

1. Create the OAuth client by running the management command: `docker-compose run --rm django python manage.py makeclient --uri http://localhost:8081/`
   - In case this step failed, you can configure the OAuth client manually: Ensure the backend is running (`docker-compose up`) and using the admin interface (`http://localhost:8000`), create an Application (located under section **DJANGO OAUTH TOOLKIT**) using the following parameters
      1. Client id: Set this to the value of `VUE_APP_OAUTH_CLIENT_ID` located in the `.env` file in frontend repo
      2. User: Click magnifying glass and select yourself
      3. Redirect uris: The uri of the frontend printed as a result of running step 1 (`npm run serve`). For example, `http://localhost:8081/`
      4. Client type: public
      5. Authorization grant type: Authorization Code
      6. Name: Any name will suffice
2. Then, simply navigate to the frontend (again for example: `http://localhost:8081/`) and follow the login flow using your previous superuser credentials.

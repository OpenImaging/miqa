# MIQA

## Develop with Docker (recommended quickstart)
This is the simplest configuration for developers to start with.

### Initial Setup
1. Run `docker-compose run --rm npm npm ci` (`docker-compose` must be at least version 1.28)
2. Run `docker-compose run --rm django ./manage.py migrate`
3. Run `docker-compose run --rm django ./manage.py createsuperuser`
   and follow the prompts to create your own user.
4. Run `docker-compose run --rm django ./manage.py makeclient --username your.email@email.com --uri http://localhost:8081/`
5. Run `docker-compose run --rm django ./manage.py populate --csv /srv/samples/new_scans_to_review.csv`. This will populate the DB with the sample scans.

### Run Application
1. Run `docker-compose up`
2. Access the site, starting at http://localhost:8081/
    - Note: When prompted to login with your "username" use your full email address (e.g. myname@someplace.com)
3. The admin console can be accessed from http://localhost:8000/admin/
4. When finished, use `Ctrl+C`

### Application Maintenance
Occasionally, new package dependencies or schema changes will necessitate
maintenance. To non-destructively update your development stack at any time:
1. Run `docker-compose pull`
2. Run `docker-compose build --pull --no-cache`
3. Run `docker-compose run --rm django ./manage.py migrate`

## Develop Natively (advanced)
This configuration still uses Docker to run attached services in the background,
but allows developers to run Python code on their native system.

### Initial Setup
1. Run `docker-compose -f ./docker-compose.yml up -d`
2. Install Python 3.8
3. Install
   [`psycopg2` build prerequisites](https://www.psycopg.org/docs/install.html#build-prerequisites)
4. Create and activate a new Python virtualenv
5. Run `pip install -e ".[dev]"`
6. Run `source ./dev/export-env.sh`
7. Run `./manage.py migrate`
8. Run `./manage.py createsuperuser` and follow the prompts to create your own user
9. Run `./manage.py makeclient --username your.email@email.com --uri http://localhost:8081/`

### Run Application
1.  Ensure `docker-compose -f ./docker-compose.yml up -d` is still active
2. Run:
   1. `source ./dev/export-env.sh`
   2. `./manage.py runserver`
3. Run in a separate terminal:
   1. `source ./dev/export-env.sh`
   2. `celery --app miqa.celery worker --loglevel INFO --without-heartbeat`
3. Run in a third terminal:
   1. `cd client`
   2. `npm run serve`
4. When finished, run `docker-compose stop`

## Remap Service Ports (optional)
Attached services may be exposed to the host system via alternative ports. Developers who work
on multiple software projects concurrently may find this helpful to avoid port conflicts.

To do so, before running any `docker-compose` commands, set any of the environment variables:
* `DOCKER_POSTGRES_PORT`
* `DOCKER_RABBITMQ_PORT`
* `DOCKER_MINIO_PORT`

The Django server must be informed about the changes:
* When running the "Develop with Docker" configuration, override the environment variables:
  * `DJANGO_MINIO_STORAGE_MEDIA_URL`, using the port from `DOCKER_MINIO_PORT`.
* When running the "Develop Natively" configuration, override the environment variables:
  * `DJANGO_DATABASE_URL`, using the port from `DOCKER_POSTGRES_PORT`
  * `DJANGO_CELERY_BROKER_URL`, using the port from `DOCKER_RABBITMQ_PORT`
  * `DJANGO_MINIO_STORAGE_ENDPOINT`, using the port from `DOCKER_MINIO_PORT`

Since most of Django's environment variables contain additional content, use the values from
the appropriate `dev/.env.docker-compose*` file as a baseline for overrides.

## Testing
### Initial Setup
tox is used to execute all tests.
tox is installed automatically with the `dev` package extra.

When running the "Develop with Docker" configuration, all tox commands must be run as
`docker-compose run --rm django tox`; extra arguments may also be appended to this form.

When running the "Develop Natively (advanced)" configuration, the shell environment
must be set up first with `source ./dev/export-env.sh`.

### Running Tests
Run `tox` to launch the full test suite.

Individual test environments may be selectively run.
This also allows additional options to be be added.
Useful sub-commands include:
* `tox -e lint`: Run only the style checks
* `tox -e test`: Run only the pytest-driven tests

To automatically reformat all code to comply with
some (but not all) of the style checks, run `tox -e format`.


## Importing / Exporting Data
In MIQA, each Project has settings that allow you to specify file paths to an import file and an export file. The import file is how you ingest data into the project and the export file will write project contents into an ingestable format. These files must be either CSV or JSON. The file paths you specify should be absolute and visible to wherever your server is running.

If you are using a production instance with native deployment, be sure that these paths are on the same machine and readable by the user that runs the Django server.

If you are using a development instance with the `docker-compose` setup, you should specify an environment variable `SAMPLES_DIR` as a directory containing any absolute paths you wish to access from the server. The `docker-compose` configuration will mount this directory as visible to the server.

## Format of the Import File
### Import CSV
If your import file is a CSV, it should contain a header row and any following rows will represent Frame objects in the Project. Each Frame object in the Project represents a single image file, and each Frame is organized into an Experiment, then into a Scan. The header row defines these columns:

```
project_name, experiment_name, scan_name, scan_type, frame_number, file_location
```
Project name: The name of the Project you create in MIQA that points to this file as its import file
Experiment name: The name you would like to apply to the experiment to which this Frame belongs
Scan name: The name you would like to apply to the scan to which this Frame belongs
Scan type: Can be one of "T1", "T2", "FMRI", "MRA", "PD", "DTI", "DWI", or any of the ncanda-specific scan types (see miqa.core.models.scan for more)
Frame number: An integer to determine the order of Frames in a Scan. If only one Frame exists, enter 0 for this value.
File location: The file path of the image file (.nii.gz, .nii, .mgz, .nrrd). This can be an absolute path (with the same restrictions as above for the import file) or a relative path to the parent of the import file itself.

### Import JSON
If your import file is a JSON, the representation for Frames is nested into the representations for Scans within Experiments within your project. Below is an example of an import JSON:

```
"projects": {
   "My Project" :{
      "experiments": {
         "Experiment One": {
            "scans": {
               "Scan One": {
                  "type": "T1",
                  "frames": {
                     0: "path/to/frame1.nii.gz",
                     1: "path/to/frame2.nii.gz",
                     2: "path/to/frame3.nii.gz
                  }
               },
               "Scan Two": {
                  "type": "T1",
                  "frames": {
                     0: "path/to/frame4.nii.gz"
                  }
               }
            }
         },
         "Experiment Two": {
            "scans": {
               "Scan Three": {
                  "type": "T1",
                  "frames": {
                     0: "path/to/frame5.nii.gz"
                  }
               }
            }
         }
      }
   }
}
```

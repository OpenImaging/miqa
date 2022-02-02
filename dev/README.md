# Development Environment
This directory contains everything required to quick start with a MIQA development server. If you would prefer to run portions of the server natively (rather than through docker-compose), refer to the advanced setup instructions in [NATIVE.md](NATIVE.md).

# Instructions
**All of these commands should be run from the `dev` directory.**

Run the following commands:
```
docker-compose build
docker-compose run --rm npm npm ci
docker-compose run --rm django ./manage.py migrate
```

**IMPORTANT**: For the next command, when you are prompted, set both the Username and Email to the same valid email address. Admin logins will break if you do not.
```
docker-compose run --rm django ./manage.py createsuperuser
```

**IMPORTANT**: For the next command, you should set the `SAMPLES_DIR` environment variable to a central location on this same machine where you will be placing all images you wish to access in MIQA, as well as any import and export files for your MIQA projects. Your docker-compose configuration will mount this directory to the django container. This means your import file can reference the same paths as on your native file system.
If you leave `SAMPLES_DIR` unset, it will default to the `samples` directory in this repository.
```
export SAMPLES_DIR=/absolute/path/to/sample_images_parent_directory/
```

**IMPORTANT**: For the next command, the trailing slash in the `uri` argument is important! Type this argument exactly as OAuth should redirect to in order to reach the npm service. In this case, npm is running on port 8081, so OAuth should redirect there after a successful login.
```
docker-compose run --rm django ./manage.py makeclient --username super.user@miqa.com --uri https://localhost:8081/
```
> Note that this command is the most important for being able to access the frontend application correctly. This command creates an OAuth Application object in your Django database. If you later find that your login procedure is not working as expected, it may be the way the Application object is configured. This is okay, because you can edit the Application object in the Django admin console. Navigate to https://localhost:8080/admin/. Click on "Applications" under "Django OAuth Toolkit". Edit the one Application object there by clicking on its row.

   **Only do the following if your login procedure is not working properly**
   1. Client id: Set this to the value of `VUE_APP_OAUTH_CLIENT_ID` located in `client/.env`.
   2. User: Click magnifying glass and select yourself
   3. Redirect uris: The uri of the frontend printed as a result of running `npm run serve` in the `client` directory. For example, `http://localhost:8081/`.
   4. Client type: public
   5. Authorization grant type: Authorization Code
   6. Name: Any name will suffice


## Run the server
Run the following command in a new shell in the same directory (this command needs to continue running as the server; use Ctrl+C to down the server).
```
docker-compose up
```
Or, if you do not need to see terminal output from this command, it may be useful to run this as a background task. Add a `-d` flag to the end of the previous command to detach the command from the shell.

Navigate to https://localhost:8000/ to log into MIQA with the credentials you supplied to the `createsuperuser` command. If your login procedure does not work as expected, be sure you check your OAuth Application object in the Django admin console.


## Adding data to MIQA
MIQA is a project-based application. To review scan images in MIQA, create a project on the homepage. Once your project is created, you will need to supply an import file path and an export file path for your project.

The import file is how you ingest data into the project and the export file will write project contents into an ingestable format. These files must be either CSV or JSON. These should be absolute file paths that point to a location within the parent directory you selected for your `SAMPLES_DIR`. Save your changes to this first project.

Before you can perform an import, be sure the import file you referenced exists and contains properly-formatted information to supply your scan images to the server and structure them within your project. To find documentation on writing an import file, reference [IMPORTING.md](../IMPORTING.md).

Once your import file is written, you may click the "Import" button on the Project page. This will ingest all the scan images you reference and structure them into Experiments and Scans within your project.

Now that data is ingested into your Project, you may now also click the "Export" button to write to your specified export file path. The export file does not need to exist already, but if it does, its contents will be overwritten by the export action. The contents written to your export file are an ingestable format that can be reused as an import file.


# Application Maintenance
Occasionally, new package dependencies or schema changes will necessitate
maintenance. To non-destructively update your development stack at any time:
1. Run `docker-compose pull`
2. Run `docker-compose build --pull --no-cache`
3. Run `docker-compose run --rm django ./manage.py migrate`


# Testing
## Initial Setup
Tox is used to execute all tests. Tox is installed automatically with the `dev` package extra.

All tox commands must be run as `docker-compose run --rm django tox`. Extra arguments may also be appended to this form, like with the following example: `docker-compose run --rm django tox -e test -- -vv -k some_test`

When running the "Develop Natively (advanced)" configuration, the shell environment
must be set up first with `source ./dev/export-env.sh`.

## Running Tests
Run `tox` to launch the full test suite.

Individual test environments may be selectively run.
This also allows additional options to be be added.
Useful sub-commands include:
* `tox -e lint`: Run only the style checks
* `tox -e test`: Run only the pytest-driven tests

To automatically reformat all code to comply with
some (but not all) of the style checks, run `tox -e format`.

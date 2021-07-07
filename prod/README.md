# Production Deployment
This directory contains everything required to deploy MIQA in production using docker-compose.

# Instructions
All of these commands should be run from the `prod` directory.

### Set the variables in .env
The `.env` file contains some default values for local testing that will need to overwritten for production deployments.
For the build and setup process these values are mostly placeholders, but they will need to be set correctly before the site is made public.

`DJANGO_EMAIL_URL` must be of the form `submission://username:password@my.smtp.server:port`. See the [documentation](https://github.com/migonzalvar/dj-email-url#supported-backends) for details with encoding special characters.

You can also specify those variables explicitly in your local shell environment instead of editing the file.
`docker-compose` will check for local shell values before defaulting to the values in `.env`.

### Build the docker image
```
docker-compose build
```

### Apply the DB migrations
Until you do this, the postgres DB is completely empty.
This will not populate any data, only set up tables.
```
docker-compose run django ./manage.py migrate
```

### Create a superuser to administer the server
**IMPORTANT**: Set both the Username and Email to the same valid email address.
Admin logins will break if you do not.
```
docker-compose run django ./manage.py createsuperuser
```

### Run the server
```
docker-compose up
```

### Set up OAuth Application
The app should now be running and accessible in your browser.
However, you still need to set up the OAuth Application before you can log in through the web client.

For this example, we will assume you are setting up `https://miqa.com/`.

Set up the application by running:
```
docker-compose run django ./manage.py makeclient --username super.user@miqa.com --uri https://miqa.com/
```

If you have problems logging in, you can reconfigure the OAuth Application from the admin console:
* In a browser, log in to the admin console at `https://miqa.com/admin` using the credentials you made earlier (email/password).
* Click on Django OAuth Toolkit > Applications.
* Click `miqa-client`.


### Set up default session
Although there are plans to support multiple sessions, currently the web client only supports one.
This session must still be created manually.

* In the admin console, click MIQA: Core > Sessions > + Add.
* Set the following values:
  * Name: whatever you like.
  * Creator: your user.
  * Import path: The path to the import CSV.
    * You should have set `$MIQA_MOUNT_DIR` when configuring the environment variables.
      This directory should contain the import CSV and all the files it would import.
      This directory is mounted in the container at the same path, so the same path should be usable inside and outside the container.
  * Export path: The path to the export CSV. See above.
* Click Save.

### Test login
* Log out of the admin console.
* Go to `https://miqa.com`. You should be redirected to a log in page.
* Log in using the credentials you made earlier. You should get a prompt that an email was sent to verify your account.
* Check your email and click the link to verify your account.
* Log in again. You should now be logged in to the app.

### Import experiments
 * Under the Experiments tab, click Import.

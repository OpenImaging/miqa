# Production Deployment
This directory contains everything required to deploy MIQA in production using docker-compose.

# Instructions
All of these commands should be run from the `prod` directory.

### Setup the configuration variables

Run:

`cp .env.template .env`

Open the `.env` file and make changes to the variables in the top section.

* `DJANGO_EMAIL_URL` must be of the form `submission://username:password@my.smtp.server:port`. See the [documentation](https://github.com/migonzalvar/dj-email-url#supported-backends) for details with encoding special characters.

You can also specify those variables explicitly in your local shell environment instead of editing the file. `docker-compose` will check for local shell values before defaulting to the values in `.env`.

### Build the docker image
```
docker-compose build
```

### Apply the DB migrations
Until you do this, the postgres DB is completely empty.
This will not populate any data, only set up tables.
```
docker-compose run --rm django ./manage.py migrate
```

### Create a superuser to administer the server
**IMPORTANT**: Set both the Username and Email to the same valid email address.
Admin logins will break if you do not.
```
docker-compose run --rm django ./manage.py createsuperuser
```

### Run the server
```
docker-compose up
```

### Set up OAuth Application
The app should now be running and accessible in your browser.
However, you still need to set up the OAuth Application before you can log in through the web client.

For this example, we will assume you are setting up `https://miqa.com/miqa2/`.

Set up the application by running:
```
docker-compose run --rm django ./manage.py makeclient --username super.user@miqa.com --uri https://miqa.com/miqa2/
```

If you have problems logging in, you can reconfigure the OAuth Application from the admin console:
* In a browser, log in to the admin console at `https://miqa.com/admin` using the credentials you made earlier (email/password).
* Click on Django OAuth Toolkit > Applications.
* Click `miqa-client`.


### Set up default session
Although there are plans to support multiple sessions, currently the web client only supports one.
This session must still be created manually:
```
docker-compose run --rm django ./manage.py populate --username super.user@miqa.com --csv /path/to/your/import.csv
```
This command will also attempt to import from the specified CSV file.
If the CSV file is invalid, it will fail and throw an error message.
However, the default session was still created, so there is no need to rerun the command.
You will be able to reconfigure and retry the import through the web UI once that is set up.

### Test login
* Log out of the admin console.
* Go to `https://miqa.com/miqa2/`. You should be redirected to a log in page.
* Log in using the credentials you made earlier. You should get a prompt that an email was sent to verify your account.
* Check your email and click the link to verify your account.
* Log in again. You should now be logged in to the app.

### Import experiments
 * Under the Experiments tab, click Import.

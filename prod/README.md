# Production Deployment
This directory contains everything required to deploy MIQA in production using docker-compose.

# Instructions
**All of these commands should be run from the `prod` directory.**


## Configure Web services

1. Run:
```
cp nginx.conf.template nginx.conf
cp .env.template .env
```

2. Edit the newly-created `prod/.env` file and replace all instances of "miqa.local" with with the desired domain name of your MIQA instance.

> You can also specify those variables explicitly in your local shell environment instead of editing the file. `docker-compose` will check for local shell values before defaulting to the values in `.env`.

3. Edit your /etc/hosts file (or non-unix equivalent) and add the following entry (note that the separator is a tab). Replace `miqa.local` with the domain name of your MIQA instance.

> 127.0.0.1 miqa.local

4. You will need SSL certificates for your server. For a real production instance, these certificates should be signed by a third-parth certificate authority. If you have third-party certificates, skip to 5. For testing a production instance, it is sufficient to create self-signed certificates.

> For a self-signed certificate, install [mkcert](https://github.com/FiloSottile/mkcert). It is recommended that you install the latest released binaries. Run `mkcert -install` to create a local certificate authority. Then, run `mkcert miqa.local` to generate some SSL certificates for your nginx instance. Replace `miqa.local` with the domain name of your MIQA instance. It should generate `miqa.local.pem` and `miqa.local-key.pem` inside the `prod` directory.

5. MIQA also requires a Mail Server for email services. One quick way to create a test mail server is by using Mailtrap. If you have some other mail server, skip to 6.

> Set up a [Mailtrap](https://mailtrap.io/) account, go to My Inbox -> SMTP/POP3 -> Integrations and select Django. Note the host, user, password, and port values. Mailtrap will now trap outgoing mail from Django, allowing you to accurately simulate use verification emails.

6. Edit `prod/.env` again and rewrite the `DJANGO_EMAIL_URL` value with the host, user, password, and port values for your mail service. `DJANGO_EMAIL_URL` must be of the form `submission://username:password@my.smtp.server:port`. See the [documentation](https://github.com/migonzalvar/dj-email-url#supported-backends) for details with encoding special characters.

7. Run the following command. Replace the `~/git/miqa/prod` portion with wherever you have cloned the miqa repository. This command will run an nginx container and mount the `miqa/prod` directory into the container's nginx configuration directory so it has access to `nginx.conf` and to your SSL certificates.

```
docker run -v ~/git/miqa/prod:/etc/nginx/conf.d:ro --network=host nginx
```

## Pull the evaluation models from git LFS
```
git lfs install
cd miqa/learning/models
git lfs fetch
git lfs pull
cd ../../..
```


## Build the docker image
```
docker-compose build
```


## Apply the DB migrations
Until you do this, the postgres DB is completely empty.
This will not populate any data, only set up tables.
```
docker-compose run --rm django ./manage.py migrate
```


## Create a superuser to administer the server
**IMPORTANT**: Set both the Username and Email to the same valid email address. Admin logins will break if you do not.
```
docker-compose run --rm django ./manage.py createsuperuser
```


## Run the server
Run the following command in a new shell in the same directory (as this command needs to continue running as the server; use Ctrl+C to stop the server gracefully).
```
docker-compose up
```
Or, if you do not need to see terminal output from this command, it may be useful to run this as a background task. Add a `-d` flag to the end of the previous command to detach the command from the shell.


## Set up OAuth Application
The app should now be running and accessible in your browser.
However, you still need to set up the OAuth Application before you can log in through the web client. Replace `miqa.local` with the domain name of your MIQA instance.

**IMPORTANT**: For the next command, the trailing slash in the `uri` argument is important! Type this argument exactly as OAuth would redirect to.
```
docker-compose run --rm django ./manage.py makeclient --username super.user@miqa.com --uri https://miqa.local/
```
> Note that this command is the most important for being able to access the frontend application correctly. This command creates an OAuth Application object in your Django database. If you later find that your login procedure is not working as expected, it may be the way the Application object is configured. This is okay, because you can edit the Application object in the Django admin console. Navigate to https://localhost:8000/admin/. Click on "Applications" under "Django OAuth Toolkit". Edit the one Application object there by clicking on its row.

   **Only do the following if your login procedure is not working properly**
   1. Client id: Set this to the value of `VUE_APP_OAUTH_CLIENT_ID` located in `client/.env`.
   2. User: Click magnifying glass and select yourself
   3. Redirect uris: The uri of the frontend printed as a result of running `npm run serve` in the `client` directory. For example, `https://miqa.local/`.
   4. Client type: public
   5. Authorization grant type: Authorization Code
   6. Name: Any name will suffice

## Test login
1. Log out of the admin console.
2. Go to `https://miqa.local/`, or whatever your domain name is set as. You should be redirected to a log in page.
3. Log in using the credentials you made earlier for the superuser account. You should get a prompt that an email was sent to verify your account.
4. Check your email (or Mailtrap inbox) and click the link to verify your account.
5. Log in again. You should now be logged in to the app.
6. You may also wish to test the functionality of allowing a new user to sign up and log in. This should be mostly the same procedure as for the superuser account, with the additional first step of clicking the "Sign Up" button in the top corner of the login page.


## Adding data to MIQA
MIQA is a project-based application. To review scan images in MIQA, create a project on the homepage. Once your project is created, you will need to supply an import file path and an export file path for your project.

The import file is how you ingest data into the project and the export file will write project contents into an ingestable format. These files must be either CSV or JSON. These should be absolute file paths that point to a location within the parent directory you selected for your `MIQA_MOUNT_DIR`. Save your changes to this first project.

Before you can perform an import, be sure the import file you referenced exists and contains properly-formatted information to supply your scan images to the server and structure them within your project. To find documentation on writing an import file, reference [IMPORTING.md](../IMPORTING.md).

Once your import file is written, you may click the "Import" button on the Project page. This will ingest all the scan images you reference and structure them into Experiments and Scans withing your project.

Now that data is ingested into your Project, you may now also click the "Export" button to write to your specified export file path. The export file does not need to exist already, but if it does, its contents will be overwritten by the "Export" action. The contents written to your export file are an ingestable format that can be recycled as an import file.


# Updating the deployment
To non-destructively update your instance at any time:
1. Pull changes from github.
2. Run `docker-compose pull`
3. Run `docker-compose build --pull --no-cache`
4. Run `docker-compose run --rm django ./manage.py migrate`
5. Run `docker-compose up`

Visit `https://miqa.local/admin/` for any admin configuration that needs to be done.

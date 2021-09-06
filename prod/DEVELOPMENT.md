# Production Environment

MIQA is deployed as a Docker image containing the application.
We also provide a docker-compose configuration that describes the required backing services.
We assume that the docker-compose stack is deployed behind nginx, which handles SSL and redirection.

To test production deployment locally, you need all of this set up.

We will assume that your local domain is `miqa.local`

# Instructions

1. Copy `.env.template` to `.env` and `nginx.conf.template` to `nginx.conf`:

```
cp .env.template .env
cp nginx.conf.template nginx.conf
```

2. Edit your /etc/hosts file (or non-unix equivalent) and add the following entry (note that the separator is a tab):

```
127.0.0.1 miqa.local
```

3. Install [mkcert](https://github.com/FiloSottile/mkcert). I recommend installing the latest released binaries.

```
mkcert -install
```

4. Use `mkcert` to generate some SSL certificates for your nginx instance. Run this command inside `miqa/prod`. It should generate `miqa.local.pem` and `miqa.local-key.pem`.

```
mkcert miqa.local
```

5. Set up a [Mailtrap](https://mailtrap.io/) account, go to My Inbox -> SMTP/POP3 -> Integrations and select Django. Grab the host, user, password, and port, then use them to rebuild the `DJANGO_EMAIL_URL` value in `.env`. Mailtrap will now trap outgoing mail from Django, allowing you to accurately simulate use verification emails.

6. Follow the instructions in `README.md` to build and set up the server.

7. Copy the command from the first line of `nginx.conf` and run it. Replace the `~/git/miqa/prod` portion with wherever you have cloned the miqa repository. This command will run an nginx container and mount the `miqa/prod` directory into the container's nginx configuration directory so it has access to `nginx.conf` and to your SSL certificates.

```
docker run -v ~/git/miqa/prod:/etc/nginx/conf.d:ro --network=host nginx
```

8. Visit `https://miqa.local/miqa2/` in the browser. You should be able to log in, have a verification email sent, click the link in your mailtrap inbox, and log in for real.

9. Visit `https://miqa.local/miqa2/admin/` for any admin configuration that needs to be done.

# Ongoing development

Be sure to run `docker-compose build` whenever you make code changes, as those changes need to be baked into the `django` image before they can be deployed to production.

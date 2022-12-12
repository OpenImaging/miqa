from django.contrib.auth.models import User
import djclick as click
from oauth2_provider.models import Application

CLIENT_ID = 'cBmD6D6F2YAmMWHNQZFPUr4OpaXVpW5w4Thod6Kj'


# create django oauth toolkit appliction (client)
@click.option(
    '--username',
    type=click.STRING,
    required=True,
    help='superuser username for application creator',
)
@click.option('--uri', type=click.STRING, required=True, help='redirect uri for application')
@click.command()
def command(username, uri):
    if Application.objects.filter(client_id=CLIENT_ID).exists():
        click.echo('The client already exists. You can administer it from the admin console.')
        return

    if username:
        user = User.objects.get(username=username)
    else:
        first_user = User.objects.first()
        if first_user:
            user = first_user

    if user:
        application = Application(
            name='miqa-client',
            client_id=CLIENT_ID,
            client_secret='',
            client_type='public',
            redirect_uris=uri,
            authorization_grant_type='authorization-code',
            user=user,
            skip_authorization=True,
        )
        application.save()

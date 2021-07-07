from django.contrib.auth.models import User
import djclick as click
from oauth2_provider.models import Application


# create django oauth toolkit appliction (client)
@click.option('--username', type=click.STRING, help='superuser username for application creator')
@click.option('--uri', type=click.STRING, help='redirect uri for application')
@click.command()
def command(username, uri):

    if username:

        user = User.objects.get(username=username)

    else:

        user = User.objects.first()

    application = Application(
        name='miqa-client',
        client_id='cBmD6D6F2YAmMWHNQZFPUr4OpaXVpW5w4Thod6Kj',
        client_secret='zNkKPQjc17WfVJjIyLlqpCNdE3LYFfOTF3crpSWsMFMBvxFsqxDz0q85Rgm'
        'BjYBX18LHB9MrygvqybJ2pmrbkAsSXquHNDVxpiEWxslp6bvQW3gWIYYuvKTyPfWvtwNU',
        client_type='public',
        redirect_uris=uri,
        authorization_grant_type='authorization-code',
        user_id=user.id,
    )

    application.save()

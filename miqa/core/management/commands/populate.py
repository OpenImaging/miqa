from django.contrib.auth.models import User
import djclick as click

from miqa.core.rest.session import import_data
from miqa.core.tests.factories import SessionFactory, UserFactory


@click.command()
@click.option('--csv', type=click.Path(exists=True))
@click.option('--username', type=click.STRING, help='username for session creator')
def command(csv, username):

    if username:

        user = User.objects.get(username=username)

    else:

        user = UserFactory()

    session = SessionFactory(name='miqa-dev', import_path=csv, export_path='.', creator=user)

    import_data(user, session)

from django.contrib.auth.models import User
import djclick as click

from miqa.core.models import Project
from miqa.core.rest.project import import_data


@click.command()
@click.option('--csv', type=click.Path(exists=True))
@click.option('--username', type=click.STRING, help='username for project creator')
def command(csv, username):

    if username:

        user = User.objects.get(username=username)

    else:

        user = User.objects.first()

    project = Project.objects.create(
        name='miqa-dev', import_path=csv, export_path='.', creator=user
    )

    import_data(user, project)

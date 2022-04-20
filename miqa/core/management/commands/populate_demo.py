from allauth.account.admin import EmailAddress
from django.contrib.auth.models import User
import djclick as click
from guardian.shortcuts import assign_perm

from miqa.core.models import Project
from miqa.core.tasks import import_data


@click.command()
def command():
    # Delete extra projects in the system that users may have created
    Project.objects.all().delete()

    # Ensure that the demo user exists
    demo_user, created = User.objects.get_or_create(
        first_name='MIQA',
        last_name='Tester',
        email='test@miqa.dev',
        username='test@miqa.dev',
    )
    demo_user.set_password('demoMe')
    demo_user.save()
    demo_user_email = EmailAddress.objects.get(email='test@miqa.dev')
    demo_user_email.verified = True
    demo_user_email.save()

    # Create Demo Project
    demo_project = Project(
        name='Demo Project',
        creator=demo_user,
        import_path='samples/demo_project.csv',
        export_path='samples/demo_export.csv',
    )
    demo_project.save()
    assign_perm('tier_2_reviewer', demo_user, demo_project)
    import_data(demo_project.id)

    print('Demo Project reset.')

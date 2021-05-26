from django.contrib.auth.models import User
import factory

from miqa.core.models import (
    Session,
    Experiment,
    Scan,
    Image,
    Site
)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

class SiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Site

    id = factory.Faker('uuid4')
    name = factory.Faker('safe_email')

    creator = factory.SubFactory(UserFactory)



class SessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Session

    id = factory.Faker('uuid4')
    name = factory.Faker('safe_email')

    creator = factory.SubFactory(UserFactory)

    import_path = '/fake/path'
    export_path = '/fake/path'

class ExperimentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Experiment

    id = factory.Faker('uuid4')
    name = factory.Faker('safe_email')
    note = factory.Faker('random_letters')

    session = factory.SubFactory(SessionFactory)

class ScanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scan

    id = factory.Faker('uuid4')
    name = factory.Faker('safe_email')
    note = factory.Faker('random_letters')

    experiment = factory.SubFactory(ExperimentFactory)
    site = factory.SubFactory(SiteFactory)

    scan_id = factory.Faker('random_letters')
    scan_type = factory.Faker('random_letters')
    decision = 'Good'
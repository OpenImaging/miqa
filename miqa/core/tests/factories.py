from django.contrib.auth.models import User
import factory

from miqa.core.models import Experiment, Image, Project, Scan, ScanDecision, Site


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
    name = factory.Faker('word')

    creator = factory.SubFactory(UserFactory)


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    id = factory.Faker('uuid4')
    name = factory.Faker('word')

    creator = factory.SubFactory(UserFactory)

    import_path = factory.Faker('file_path')
    export_path = factory.Faker('file_path')


class ExperimentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Experiment

    id = factory.Faker('uuid4')
    name = factory.Faker('word')
    note = factory.Faker('sentence')

    project = factory.SubFactory(ProjectFactory)


class ScanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scan

    id = factory.Faker('uuid4')

    experiment = factory.SubFactory(ExperimentFactory)
    scan_type = factory.Faker('pystr')


class ScanDecisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScanDecision

    scan = factory.SubFactory(ScanFactory)
    creator = factory.SubFactory(UserFactory)


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    id = factory.Faker('uuid4')
    raw_path = factory.Faker('file_path')
    frame_number = factory.Faker('pyint')

    scan = factory.SubFactory(ScanFactory)

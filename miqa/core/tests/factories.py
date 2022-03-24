from django.contrib.auth.models import User
from django.utils import timezone
import factory

from miqa.core.models import Experiment, Frame, Project, Scan, ScanDecision


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    id = factory.Faker('uuid4')
    name = factory.Faker('word')

    creator = factory.SubFactory(UserFactory)

    import_path = factory.Faker('file_path')
    export_path = factory.Faker('file_path')
    default_email_recipients = factory.Faker('email')


class ExperimentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Experiment

    id = factory.Faker('uuid4')
    name = factory.Faker('word')
    note = factory.Faker('sentence')

    project = factory.SubFactory(ProjectFactory)
    lock_time = timezone.now()


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


class FrameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Frame

    id = factory.Faker('uuid4')
    raw_path = factory.Faker('file_path')
    frame_number = factory.Faker('pyint')

    scan = factory.SubFactory(ScanFactory)

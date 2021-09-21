from django.contrib.auth.models import User
import factory

from miqa.core.models import Annotation, Experiment, Image, Scan, ScanNote, Project, Site


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
    site = factory.SubFactory(SiteFactory)

    scan_id = factory.Faker('pystr')
    scan_type = factory.Faker('pystr')


class AnnotationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Annotation

    scan = factory.SubFactory(ScanFactory)
    creator = factory.SubFactory(UserFactory)


class NoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScanNote

    id = factory.Faker('uuid4')
    note = factory.Faker('sentence')

    creator = factory.SubFactory(UserFactory)
    scan = factory.SubFactory(ScanFactory)

    @factory.lazy_attribute
    def initials(self):
        return f'{self.creator.first_name[0]}{self.creator.last_name[0]}'


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    id = factory.Faker('uuid4')
    raw_path = factory.Faker('file_path')
    name = factory.Faker('word')

    scan = factory.SubFactory(ScanFactory)

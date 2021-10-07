from uuid import uuid4

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django_extensions.db.models import TimeStampedModel

from miqa.core.models.scan import SCAN_TYPES
from miqa.learning.evaluation_models import available_evaluation_models


def default_evaluation_model_mapping():
    return {
        'T1': 'MIQAT1-0',
        'T2': 'MIQAT1-0',
        'FMRI': 'MIQAT1-0',
        'MRA': 'MIQAT1-0',
        'PD': 'MIQAT1-0',
        'DTI': 'MIQAT1-0',
        'DWI': 'MIQAT1-0',
        'ncanda-t1spgr-v1': 'MIQAT1-0',
        'ncanda-mprage-v1': 'MIQAT1-0',
        'ncanda-t2fse-v1': 'MIQAT1-0',
        'ncanda-dti6b500pepolar-v1': 'MIQAT1-0',
        'ncanda-dti30b400-v1': 'MIQAT1-0',
        'ncanda-dti60b1000-v1': 'MIQAT1-0',
        'ncanda-grefieldmap-v1': 'MIQAT1-0',
        'ncanda-rsfmri-v1': 'MIQAT1-0',
    }


class Project(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(User, on_delete=models.PROTECT)
    archived = models.BooleanField(default=False)
    import_path = models.CharField(max_length=500)
    export_path = models.CharField(max_length=500)
    evaluation_models = models.JSONField(default=default_evaluation_model_mapping)

    def __str__(self):
        return self.name

    def clean(self):
        if not isinstance(self.evaluation_models, dict):
            raise ValidationError('Specify evaluation models as a dictionary.')
        scan_types = [x[0] for x in SCAN_TYPES]
        if any(key not in scan_types for key in self.evaluation_models.keys()):
            raise ValidationError(
                f'Keys in evaluation models must be valid scan types. '
                f'Valid scan types are {scan_types}.'
            )
        # do we want to demand that every scan type has a chosen evaluation model?
        if any(
            value is None or value not in available_evaluation_models
            for value in self.evaluation_models.values()
        ):
            raise ValidationError(
                f'Values in evaluation models must be valid evalution model names. '
                f'Valid evaluation model names are {available_evaluation_models.keys()}'
            )

        super().clean()

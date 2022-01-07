from uuid import uuid4

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django_extensions.db.models import TimeStampedModel
from guardian.shortcuts import assign_perm, get_perms, get_users_with_perms, remove_perm

from miqa.core.models.scan import SCAN_TYPES, Scan
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
    global_import_export = models.BooleanField(default=False)
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

    def get_read_permission_groups():
        return ['collaborator', 'tier_1_reviewer', 'tier_2_reviewer']

    def get_review_permission_groups():
        return ['tier_1_reviewer', 'tier_2_reviewer']

    def get_user_role(self, user):
        perm_order = Project.get_read_permission_groups()
        return sorted(
            get_perms(user, self),
            key=lambda perm: perm_order.index(perm) if perm in perm_order else -1,
        )[-1]

    def get_status(self):
        tier_2_reviewers = [
            user.id for user in get_users_with_perms(self, only_with_perms_in=['tier_2_reviewer'])
        ]
        scans_in_project = Scan.objects.filter(
            experiment__in=self.experiments.all()
        ).prefetch_related('decisions')
        complete_scans_in_project = [
            scan
            for scan in scans_in_project
            if scan.decisions.count() > 0
            and scan.decisions.latest('created').creator.id in tier_2_reviewers
        ]
        return {
            'total_scans': scans_in_project.count(),
            'total_complete': len(complete_scans_in_project),
        }

    def update_group(self, group_name, user_list):
        if group_name not in Project.get_read_permission_groups():
            raise ValueError(f'Error: {group_name} is not a valid group on this Project.')

        old_list = get_users_with_perms(self, only_with_perms_in=[group_name])
        for previously_permitted_user in old_list:
            if previously_permitted_user.username not in user_list:
                remove_perm(group_name, previously_permitted_user, self)

        for username in user_list:
            new_permitted_user = User.objects.get(username=username)
            if new_permitted_user not in old_list:
                assign_perm(group_name, new_permitted_user, self)

    class Meta:
        permissions = (
            ('collaborator', 'Collaborator'),
            ('tier_1_reviewer', 'Tier 1 Reviewer'),
            ('tier_2_reviewer', 'Tier 2 Reviewer'),
        )

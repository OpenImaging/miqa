from django.contrib.auth.models import User
from django.db.models import Model
from django.shortcuts import get_object_or_404
from django.utils.functional import wraps
from guardian.shortcuts import get_perms
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import View

from miqa.core.models import Experiment, Project


def project_permission_required(
    read_access=True, review_access=False, superuser_access=False, **kwargs
):
    def decorator(view_func):
        def _wrapped_view(viewset, *args, **kwargs):
            lookup_mapping = {
                'ProjectViewSet': 'pk',
                'ExperimentViewSet': 'experiments__pk',
                'ScanViewSet': 'experiments__scans__pk',
                'ScanDecisionViewSet': 'experiments__scans__decisions__pk',
                'FrameViewSet': 'experiments__scans__frames__pk',
            }
            lookup_dict = {lookup_mapping[viewset.__class__.__name__]: kwargs['pk']}
            project = get_object_or_404(Project, **lookup_dict)

            user = viewset.request.user
            user_perms_on_project = get_perms(user, project)
            has_review_perm = all(
                [
                    perm not in user_perms_on_project
                    for perm in Project.get_review_permission_groups()
                ]
            )
            has_read_perm = all(
                [perm not in user_perms_on_project for perm in Project.get_read_permission_groups()]
            )
            error_response = Response(status=status.HTTP_401_UNAUTHORIZED)

            if (
                (superuser_access and not user.is_superuser)
                or (review_access and has_review_perm)
                or (read_access and has_read_perm)
            ):
                return error_response

            return view_func(viewset, *args, **kwargs)

        return wraps(view_func)(_wrapped_view)

    return decorator


class ArchivedProject(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'This experiment belongs to an archived project.'


class LockContention(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'This experiment lock is held by a different user.'


class NotLocked(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You must lock the experiment before performing this action.'


class UserHoldsExperimentLock(BasePermission):
    """
    Permission class for experiment lock policy.

    This permission class enforces the exclusive write lock policy on a Project
    and all objects belonging to that Project. Any model type that wants to make
    use of this class should expose a `project` property on itself that returns
    the Project to which it belongs.

    Rather than just returning a regular 403, this class throws an exception, so
    that it can provide a more specific error message and status code (HTTP 409 Conflict).
    """

    def has_object_permission(self, request: Request, view: View, obj: Model):
        if request.method in SAFE_METHODS:
            return True

        experiment: Experiment = obj if isinstance(obj, Experiment) else obj.experiment
        if experiment.lock_owner is None:
            raise NotLocked()
        if experiment.lock_owner != request.user:
            raise LockContention()

        return True


def ensure_experiment_lock(obj: Model, user: User) -> None:
    """
    Raise an exception if the given user does not possess the experiment lock.

    This should be called by all REST `create` methods that correspond to an object
    within a Experiment, as new object creation policies are not handled by the
    `UserHoldsExperimentLock` class.
    """
    experiment: Experiment = obj if isinstance(obj, Experiment) else obj.experiment
    if experiment.lock_owner is None:
        raise NotLocked()
    if experiment.lock_owner != user:
        raise LockContention()

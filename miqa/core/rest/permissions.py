from typing import Union

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils.functional import wraps
from django.views.generic import View
from guardian.shortcuts import get_perms
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.response import Response

from miqa.core.models import Experiment, Project, Scan


def has_review_perm(user_perms_on_project):
    return any(perm in user_perms_on_project for perm in Project().get_review_permission_groups())


def has_read_perm(user_perms_on_project):
    return any(perm in user_perms_on_project for perm in Project().get_read_permission_groups())


def project_permission_required(review_access=False, superuser_access=False, **decorator_kwargs):
    def decorator(view_func):
        def _wrapped_view(viewset, *args, **wrapped_view_kwargs):
            if decorator_kwargs:
                lookup_dict = {
                    key: wrapped_view_kwargs[value] for key, value in decorator_kwargs.items()
                }
            else:
                lookup_dict = {'pk': wrapped_view_kwargs['pk']}
            project = get_object_or_404(Project, **lookup_dict)

            user = viewset.request.user
            user_perms_on_project = get_perms(user, project)
            review_perm = has_review_perm(user_perms_on_project)
            read_perm = has_read_perm(user_perms_on_project)

            if (
                (superuser_access and not user.is_superuser)
                or (review_access and not review_perm)
                or not read_perm
            ):
                return Response(status=status.HTTP_403_FORBIDDEN)

            return view_func(viewset, *args, **wrapped_view_kwargs)

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

    def has_object_permission(self, request: Request, view: View, obj: Union[Experiment, Scan]):
        if request.method in SAFE_METHODS:
            return True

        experiment: Experiment = obj if isinstance(obj, Experiment) else obj.experiment
        if experiment.lock_owner is None:
            raise NotLocked()
        if experiment.lock_owner != request.user:
            raise LockContention()

        return True


def ensure_experiment_lock(obj: Union[Experiment, Scan], user: User) -> None:
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

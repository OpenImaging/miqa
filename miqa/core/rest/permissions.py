from django.contrib.auth.models import User
from django.db.models import Model
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import View

from miqa.core.models import Session


class LockContention(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'This session lock is held by a different user.'


class NotLocked(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You must lock the session before performing this action.'


class UserHoldsSessionLock(BasePermission):
    """
    Permission class for session lock policy.

    This permission class enforces the exclusive write lock policy on a Session
    and all objects belonging to that Session. Any model type that wants to make
    use of this class should expose a `session` property on itself that returns
    the Session to which it belongs.

    Rather than just returning a regular 403, this class throws an exception, so
    that it can provide a more specific error message and status code (HTTP 409 Conflict).
    """

    def has_object_permission(self, request: Request, view: View, obj: Model):
        if request.method in SAFE_METHODS:
            return True

        session: Session = obj if isinstance(obj, Session) else obj.session
        if session.lock_owner is None:
            raise NotLocked()
        if session.lock_owner != request.user:
            raise LockContention()

        return True


def ensure_session_lock(obj: Model, user: User) -> None:
    """
    Raise an exception if the given user does not possess the session lock.

    This should be called by all REST `create` methods that correspond to an object
    within a Session, as new object creation policies are not handled by the
    `UserHoldsSessionLock` class.
    """
    session: Session = obj if isinstance(obj, Session) else obj.session
    if session.lock_owner is None:
        raise NotLocked()
    if session.lock_owner != user:
        raise LockContention()

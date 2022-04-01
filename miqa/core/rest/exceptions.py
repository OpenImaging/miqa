import logging
import uuid

from django.http.response import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger('MIQA')


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if not isinstance(exc, APIException) and not isinstance(exc, Http404):
        exception_identifier = uuid.uuid4()
        logger.exception(f'Error {exception_identifier}: {exc} / {context}')
        return Response(
            data={
                'detail': 'Unexpected server error. '
                f'Refer to error {exception_identifier} in the server logs.'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return response

import logging
import uuid
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from rest_framework.response import Response


logger = logging.getLogger('MIQA')


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If an excpetion is unexpected, it will not be an APIException
    if not isinstance(exc, APIException):
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

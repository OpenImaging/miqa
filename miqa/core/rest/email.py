from email.mime.image import MIMEImage
import mimetypes
import re

from django.core.mail import EmailMultiAlternatives
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class EmailView(APIView):
    def post(self, request, format=None):

        print(request.data['screenshots'])

        msg = EmailMultiAlternatives(
            request.data['subject'],
            request.data['body'],
            'example@kitware.com',  # TODO: replace
            request.data['to'],
            bcc=request.data['bcc'],
            cc=request.data['cc'],
        )

        for index, screenshot in enumerate(request.data['screenshots']):

            # parse data uri to extract mime type and base64 data
            # assumptions: mime type is image/jpeg or image/png
            match = re.search(r'^data\:(?P<mime>.+);base64,(?P<data>.+)$', screenshot['dataURL'])

            if match:

                mime = match.group('mime')
                img = MIMEImage(match.group('data'), mime.split('/')[1])
                img.add_header('Content-Id', f'<file{index}>')
                img.add_header(
                    'Content-Disposition',
                    'inline',
                    filename=screenshot['name'] + mimetypes.guess_extension(mime),
                )
                msg.attach(img)

        msg.send()

        return Response(status=status.HTTP_204_NO_CONTENT)

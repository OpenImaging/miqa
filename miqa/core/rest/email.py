from base64 import b64decode
from email.mime.image import MIMEImage
import mimetypes
import re

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class EmailView(APIView):
    def post(self, request, format=None):
        msg = EmailMultiAlternatives(
            request.data['subject'],
            request.data['body'],
            settings.DEFAULT_FROM_EMAIL,
            request.data['to'],
            bcc=request.data['bcc'],
            cc=request.data['cc'],
            reply_to=[request.user.email],
        )

        for index, screenshot in enumerate(request.data['screenshots']):
            # parse data uri to extract mime type and base64 data
            # assumptions: mime type is image/jpeg or image/png
            match = re.fullmatch(
                r'data:(?P<mime>[\w/\-\.]+);?(\w+),(?P<data>.*)', screenshot['dataURL']
            )

            if match:
                b64_data = match.group('data')
                data = b64decode(b64_data)
                mime = match.group('mime')
                img = MIMEImage(data, mime.split('/')[1])
                img.add_header('Content-Id', f'<file{index}>')
                img.add_header(
                    'Content-Disposition',
                    'inline',
                    filename=screenshot['name'] + mimetypes.guess_extension(mime),
                )
                msg.attach(img)

        msg.send()

        return Response(status=status.HTTP_204_NO_CONTENT)

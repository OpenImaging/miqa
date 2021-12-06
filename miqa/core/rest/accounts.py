from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render, redirect
from django.views.generic.base import TemplateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class AccountInactiveView(TemplateView):
    template_name = 'account_inactive.html'


class AccountActivateView(TemplateView):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated and request.user.is_superuser:
            return redirect('home')
        return super(AccountActivateView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        email = kwargs['email']
        user = User.objects.get(email=email)

        return render(
            request,
            'account_activate.html',
            {'user': user},
        )

    def post(self, request, *args, **kwargs):
        email = kwargs['email']
        user = User.objects.get(email=email)

        req_body = request.POST.dict()
        user.is_active = req_body.get('active_status') == 'APPROVED'
        rejection_reason = req_body.get('rejection_reason')
        self.send_notification(user, user.is_active, rejection_reason)
        user.save()

        return render(
            request,
            'account_reviewed.html',
            {'user': user},
        )

    def send_notification(self, user, activated, rejection_reason):
        if activated:
            email_content = (
                'An administrator has approved your account.'
                ' You may now use your credentials to log in to MIQA.'
            )
            email_subject = 'MIQA Account Approved'
        else:
            rejection_string = (
                ' The following reason was provided for this rejection: \"'
                + rejection_reason
                + '\". \n\n'
                if rejection_reason
                else ''
            )
            email_content = (
                'An administrator has rejected your account.'
                f'{rejection_string}'
                ' Your account will remain inactive. If you believe this is a mistake,'
                ' contact your MIQA administrator.'
            )
            email_subject = 'MIQA Account Rejected'

        msg = EmailMultiAlternatives(
            email_subject,
            email_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        msg.send()


class LogoutView(APIView):
    def post(self, request):
        if request.user.is_authenticated:
            logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)

from allauth.account.forms import SignupForm
from allauth.account.views import LoginView
from django import forms
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render
from django.views.generic.base import TemplateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class AccountInactiveView(TemplateView):
    template_name = 'account_inactive.html'


class AccountActivateView(TemplateView):
    template_name = 'account_activate.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            self.template_name = 'login_before_activating.html'
        return super(AccountActivateView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        email = kwargs['email']
        user = User.objects.get(email=email)

        return render(
            request,
            self.template_name,
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


class DemoModeLoginView(LoginView):
    def get_context_data(self, **kwargs):
        ret = super(LoginView, self).get_context_data(**kwargs)
        ret.update(
            {
                'messages': [
                    'Welcome to the MIQA demo. You may login as the demo user with \
                        the following credentials: test@miqa.dev / demoMe',
                    'Please note that the projects in this demo are public and regularly deleted. \
                        Any changes you make will be lost.',
                    'To schedule a detailed walkthrough, \
                        contact us at https://kitware.com/contact/.',
                ]
            }
        )
        return ret


class AccountSignupForm(SignupForm):
    first_name = forms.CharField(
        label=('First Name'),
        min_length=1,
        widget=forms.TextInput(attrs={'placeholder': ('First name')}),
    )
    last_name = forms.CharField(
        label=('Last Name'),
        min_length=1,
        widget=forms.TextInput(attrs={'placeholder': ('Last name')}),
    )

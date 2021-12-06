from allauth.account.signals import email_confirmed
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from rest_framework.reverse import reverse_lazy


@receiver(email_confirmed)
def require_admin_approval(sender, **kwargs):
    # make user inactive by default
    user = kwargs['email_address'].user
    user.is_active = False
    user.save()

    activation_link = reverse_lazy(
        'account-activate', args=[kwargs['email_address']], request=kwargs['request']
    )
    admins = User.objects.filter(is_superuser=True)

    msg = EmailMultiAlternatives(
        'MIQA Account Approval - New User',
        f'A new user with the email {kwargs["email_address"]} has created '
        'an account in MIQA. As an administrative user, it is your responsibility '
        'to activate this account if you believe this user is legitimate. '
        'If you believe this account should not be activated, reach out to this user'
        f'{" and other administrators." if len(admins) > 1 else "."} '
        '\n\n '
        f'To activate this account, visit {activation_link}. '
        '\n\n '
        'Thank you for using MIQA! ',
        settings.DEFAULT_FROM_EMAIL,
        [admin.email for admin in admins],
    )
    msg.send()

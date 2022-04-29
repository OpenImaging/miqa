from allauth.account.signals import email_confirmed
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from rest_framework.reverse import reverse_lazy


@receiver(email_confirmed)
def require_admin_approval(sender, **kwargs):
    admins = User.objects.filter(is_superuser=True)

    if not settings.DEMO_MODE:
        # make user inactive by default
        user = kwargs['email_address'].user
        user.is_active = False
        user.save()

        activation_link = reverse_lazy(
            'account-activate', args=[kwargs['email_address']], request=kwargs['request']
        )

        email_content = f'A new user with the email {kwargs["email_address"]} has created '
        'an account in MIQA. As an administrative user, it is your responsibility '
        'to activate this account if you believe this user is legitimate. '
        'If you believe this account should not be activated, reach out to this user'
        f'{" and other administrators." if len(admins) > 1 else "."} '
        '\n\n '
        f'To activate this account, visit {activation_link} '
        '\n\n '
        'Thank you for using MIQA! '
    else:
        email_content = f'A new user with the email {kwargs["email_address"]} has created '
        'an account in MIQA. Since this instance is in demo mode, you do not need to '
        'activate this account. This email is a notification of the change; '
        'no further action is required.'
        '\n\n '
        'Thank you for using MIQA! '

    msg = EmailMultiAlternatives(
        'MIQA Account Approval - New User',
        email_content,
        settings.DEFAULT_FROM_EMAIL,
        [admin.email for admin in admins],
    )
    msg.send()

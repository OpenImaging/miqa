from django.dispatch import receiver
from allauth.account.signals import email_confirmed


@receiver(email_confirmed)
def require_admin_approval(sender, **kwargs):
    user = kwargs['email_address'].user
    user.is_active = False
    user.save()

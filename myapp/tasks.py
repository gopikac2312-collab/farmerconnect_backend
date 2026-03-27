from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_verification_email(email, link):
    send_mail(
        "Verify your email",
        f"Click the link to verify your email:\n{link}",
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

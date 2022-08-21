from django.core.mail import send_mail
from decouple import config


class Util:
    @staticmethod
    def send_email_register(data):

        email_response = send_mail(
            data['email_subject'],
            data['email_body'],
            config('EMAIL_HOST_USER'),
            [data['email_receiver']],
            fail_silently=False,
        )
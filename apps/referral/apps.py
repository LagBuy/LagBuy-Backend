from django.apps import AppConfig


class ReferralConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.referral'

    def ready(self) -> None:
        import apps.referral.signals
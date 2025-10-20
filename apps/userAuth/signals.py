from django.db.models.signals import post_migrate
from django.dispatch import receiver
from apps.userAuth.models import Role


@receiver(post_migrate)
def create_default_roles(sender, **kwargs):
    """Create default roles after migrations"""
    if sender.name == 'apps.userAuth':
        default_roles = ['user', 'rider', 'vendor']
        
        for role_name in default_roles:
            Role.objects.get_or_create(name=role_name)

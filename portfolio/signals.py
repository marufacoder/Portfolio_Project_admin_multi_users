from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, raw=False, **kwargs):
    """Every new user (registered, created by an admin, or createsuperuser) gets a portfolio."""
    if created and not raw:
        Profile.objects.get_or_create(user=instance)


@receiver(post_delete, sender=Profile)
def delete_profile_files(sender, instance, **kwargs):
    """Remove uploaded files from disk when a portfolio is deleted."""
    for field_name in ("profile_picture", "cv"):
        stored_file = getattr(instance, field_name)
        if stored_file:
            stored_file.delete(save=False)

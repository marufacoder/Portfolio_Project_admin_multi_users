"""Authentication backend that accepts a username *or* an email address."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        if username is None:
            username = kwargs.get(user_model.USERNAME_FIELD)
        if username is None or password is None:
            return None

        identifier = str(username).strip()
        if not identifier:
            return None

        candidates = list(
            user_model._default_manager.filter(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            )
        )
        for user in candidates:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

        if not candidates:
            # Run the hasher once so unknown accounts take about as long as
            # known ones (mitigates user enumeration through timing).
            user_model().set_password(password)
        return None

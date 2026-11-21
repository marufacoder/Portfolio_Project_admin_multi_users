"""Ownership rules, kept in one place so they are easy to audit and change.

* A regular user can see and change only their own portfolio.
* An administrator (``is_superuser`` or ``is_staff``) can see and change all
  portfolios. Change ``is_portfolio_admin`` if you want superusers only.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def is_portfolio_admin(user):
    return bool(
        user.is_authenticated and user.is_active and (user.is_superuser or user.is_staff)
    )


def can_manage_profile(user, profile):
    if not user.is_authenticated:
        return False
    return is_portfolio_admin(user) or profile.user_id == user.pk


def admin_required(view_func):
    """Require a logged-in administrator; everyone else gets a 403 page."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_portfolio_admin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped

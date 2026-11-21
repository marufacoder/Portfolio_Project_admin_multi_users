from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import LoginForm, RegistrationForm


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def register(request):
    """Create a new account (and, via a signal, an empty portfolio)."""
    if request.user.is_authenticated:
        return redirect("portfolio:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
            messages.success(
                request,
                "Welcome! Your account is ready. Start by filling in your profile.",
            )
            return redirect("portfolio:dashboard")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})

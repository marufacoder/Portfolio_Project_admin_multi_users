from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class RegistrationForm(UserCreationForm):
    """Sign-up form: username, email and password (entered twice)."""

    email = forms.EmailField(
        required=True,
        help_text="Used to sign in and must be unique.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email


class LoginForm(AuthenticationForm):
    """Login form that accepts either a username or an email address."""

    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(attrs={"autofocus": True}),
    )

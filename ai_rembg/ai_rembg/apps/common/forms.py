# from django import forms
from django.contrib.auth.forms import UserChangeForm

from .models import User


class CustomUserChangeForm(UserChangeForm):  # type: ignore[type-arg]
    class Meta(UserChangeForm.Meta):
        model = User

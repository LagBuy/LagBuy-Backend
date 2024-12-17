from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating users on the django admin dashboard"""
    class Meta(UserCreationForm):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'username', 'role', 'phone_number')

class CustomUserChangeForm(UserChangeForm):
    """Custom form to update user info on django admin dashboard"""
    class Meta:
        model = CustomUser
        fields = UserChangeForm.Meta.fields
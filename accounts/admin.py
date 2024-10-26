from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser
from .forms import CustomUserChangeForm, CustomUserCreationForm

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = [
        'email', 'first_name', 'last_name', 'username', 'phone_number', 'role', 'is_active',
    ]
    fieldsets = ((None, {"fields": ('email', 'first_name', 'last_name', 'username', 'role', 'phone_number')}),)     # edit
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {"fields": ('email', 'first_name', 'last_name', 'role', 'phone_number')}),)


admin.site.register(CustomUser, CustomUserAdmin)

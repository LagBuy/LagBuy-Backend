from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, Role
from .forms import CustomUserChangeForm, CustomUserCreationForm


class RoleFilter(admin.SimpleListFilter):
    """Custom filter for user roles"""
    title = 'role'
    parameter_name = 'role'

    def lookups(self, request, model_admin):
        """Return a list of tuples for the filter options"""
        roles = Role.objects.all()
        return [(role.id, role.name) for role in roles]

    def queryset(self, request, queryset):
        """Filter the queryset based on the selected role"""
        if self.value():
            return queryset.filter(roles__id=self.value())
        return queryset


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ('email', 'get_full_name', 'get_roles', 'is_staff', 'is_superuser')
    list_filter = (RoleFilter, 'is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Roles', {'fields': ('roles',)}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions', 'roles')

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add user statistics"""
        extra_context = extra_context or {}
        
        # Get total users
        total_users = CustomUser.objects.count()
        
        # Get users by role
        roles_stats = []
        roles = Role.objects.all()
        for role in roles:
            count = CustomUser.objects.filter(roles=role).count()
            roles_stats.append({
                'name': role.name,
                'count': count
            })
        
        # Get users with no roles
        no_role_count = CustomUser.objects.filter(roles__isnull=True).count()
        if no_role_count > 0:
            roles_stats.append({
                'name': 'No Role',
                'count': no_role_count
            })
        
        # Get new users today
        today = timezone.now().date()
        new_users_today = CustomUser.objects.filter(created_at__date=today).count()
        
        # Get new users in the last 7 days (daily breakdown)
        daily_stats = []
        for i in range(6, -1, -1):  # Last 7 days including today
            date = today - timedelta(days=i)
            count = CustomUser.objects.filter(created_at__date=date).count()
            daily_stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'day': date.strftime('%A'),
                'count': count
            })
        
        # Get new users in the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_users_last_30_days = CustomUser.objects.filter(created_at__gte=thirty_days_ago).count()
        
        extra_context['total_users'] = total_users
        extra_context['roles_stats'] = roles_stats
        extra_context['new_users_today'] = new_users_today
        extra_context['daily_stats'] = daily_stats
        extra_context['new_users_last_30_days'] = new_users_last_30_days
        
        return super().changelist_view(request, extra_context=extra_context)

    def get_full_name(self, obj):
        """Display user's full name from their profile"""
        try:
            if hasattr(obj, 'user_profile'):
                return f"{obj.user_profile.first_name} {obj.user_profile.last_name}"
            elif hasattr(obj, 'vendor_profile') and obj.vendor_profile.business_name:
                return obj.vendor_profile.business_name
            elif hasattr(obj, 'rider_profile'):
                return "Rider Profile"
            return "No Profile"
        except Exception:
            return "No Profile"
    get_full_name.short_description = 'Full Name'

    def get_roles(self, obj):
        """Display all roles assigned to the user"""
        roles = obj.roles.all()
        if roles:
            return ", ".join([role.name for role in roles])
        return "No Roles"
    get_roles.short_description = 'Roles'


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role)

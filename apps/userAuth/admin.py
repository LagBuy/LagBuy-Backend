from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import csv
from datetime import datetime
from django.http import HttpResponse
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

    actions = ['export_users_csv']

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

    def export_users_csv(self, request, queryset):
        """Admin action to export selected users and their profiles to CSV.

        Usage: filter users by role using the RoleFilter, select desired users
        (or use the 'select all' option to select filtered results), then choose this
        action. The CSV will include email, roles and any related profile fields for
        user (buyer), vendor and rider profiles when they exist.
        """
        # Prepare response with BOM for Excel compatibility
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        response['Content-Disposition'] = f'attachment; filename=users_export_{timestamp}.csv'
        response.write('\ufeff')

        writer = csv.writer(response)

        headers = [
            'email',
            'roles',
            'profile_type',
            # Buyer profile fields
            'first_name', 'last_name', 'phone_number',
            # Vendor profile fields
            'business_name', 'business_address', 'business_city', 'business_state', 'vendor_is_verified', 'vendor_bank_code', 'vendor_account_number', 'vendor_plan_type',
            # Rider profile fields
            'rider_phone_number2', 'rider_bank_name', 'rider_account_number', 'rider_account_name', 'rider_is_verified',
        ]
        writer.writerow(headers)

        for user in queryset.select_related('user_profile', 'vendor_profile', 'rider_profile').prefetch_related('roles'):
            roles = ", ".join([r.name for r in user.roles.all()])

            # Initialize all fields to empty string
            first_name = last_name = phone_number = gender = dob = city = state = address = image = ''
            business_name = business_address = business_city = business_state = vendor_is_verified = vendor_bank_code = vendor_account_number = vendor_plan_type = ''
            rider_phone_number2 = rider_nin = rider_next_of_kin = rider_nok_phonenumber = rider_motorcycle_type = rider_motorcycle_brand = rider_plate_number = rider_bank_name = rider_account_number = rider_account_name = rider_is_verified = ''

            profile_type = ''

            # Buyer profile
            if hasattr(user, 'user_profile') and getattr(user, 'user_profile'):
                up = user.user_profile
                profile_type = profile_type + 'buyer ' if profile_type == '' else profile_type + ', buyer'
                first_name = getattr(up, 'first_name', '') or ''
                last_name = getattr(up, 'last_name', '') or ''
                phone_number = getattr(up, 'phone_number', '') or ''
                
            # Vendor profile
            if hasattr(user, 'vendor_profile') and getattr(user, 'vendor_profile'):
                vp = user.vendor_profile
                profile_type = profile_type + 'vendor ' if profile_type == '' else profile_type + ', vendor'
                business_name = getattr(vp, 'business_name', '') or ''
                # use property `address` if available, else business_address
                business_address = getattr(vp, 'address', '') or getattr(vp, 'business_address', '') or ''
                business_city = getattr(vp, 'business_location_city', '') or ''
                business_state = getattr(vp, 'business_location_state', '') or ''
                vendor_is_verified = str(getattr(vp, 'is_verified', ''))
                vendor_bank_code = getattr(vp, 'bank_code', '') or ''
                vendor_account_number = getattr(vp, 'account_number', '') or ''
                vendor_plan_type = getattr(vp, 'plan_type', '') or ''

            # Rider profile
            if hasattr(user, 'rider_profile') and getattr(user, 'rider_profile'):
                rp = user.rider_profile
                profile_type = profile_type + 'rider ' if profile_type == '' else profile_type + ', rider'
                rider_phone_number2 = getattr(rp, 'phone_number2', '') or ''
                rider_bank_name = getattr(rp, 'bank_name', '') or ''
                rider_account_number = getattr(rp, 'account_number', '') or ''
                rider_account_name = getattr(rp, 'account_name', '') or ''
                rider_is_verified = str(getattr(rp, 'is_verified', ''))

            row = [
                user.email,
                roles,
                profile_type.strip(),
                first_name,
                last_name,
                phone_number,
                business_name,
                business_address,
                business_city,
                business_state,
                vendor_is_verified,
                vendor_bank_code,
                vendor_account_number,
                vendor_plan_type,
                rider_phone_number2,
                rider_bank_name,
                rider_account_number,
                rider_account_name,
                rider_is_verified,
            ]

            writer.writerow(row)

        return response


def export_users_csv(modeladmin, request, queryset):
    """Admin action to export selected users and their profiles to CSV.

    Expected usage: filter users by role using the RoleFilter, select desired users
    (or use the 'select all' option to select filtered results), then choose this
    action. The CSV will include email, roles and any related profile fields for
    user (buyer), vendor and rider profiles when they exist.
    """
    # Prepare response with BOM for Excel compatibility
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    response['Content-Disposition'] = f'attachment; filename=users_export_{timestamp}.csv'
    response.write('\ufeff')

    writer = csv.writer(response)

    headers = [
        'email',
        'roles',
        'profile_type',
        # Buyer profile fields
        'first_name', 'last_name', 'phone_number', 'gender', 'dob', 'city', 'state', 'address', 'image',
        # Vendor profile fields
        'business_name', 'business_address', 'business_city', 'business_state', 'vendor_is_verified', 'vendor_bank_code', 'vendor_account_number', 'vendor_plan_type',
        # Rider profile fields
        'rider_phone_number2', 'rider_nin', 'rider_next_of_kin', 'rider_nok_phonenumber', 'rider_motorcycle_type', 'rider_motorcycle_brand', 'rider_plate_number', 'rider_bank_name', 'rider_account_number', 'rider_account_name', 'rider_is_verified',
    ]
    writer.writerow(headers)

    for user in queryset.select_related('user_profile', 'vendor_profile', 'rider_profile').prefetch_related('roles'):
        roles = ", ".join([r.name for r in user.roles.all()])

        # Initialize all fields to empty string
        first_name = last_name = phone_number = gender = dob = city = state = address = image = ''
        business_name = business_address = business_city = business_state = vendor_is_verified = vendor_bank_code = vendor_account_number = vendor_plan_type = ''
        rider_phone_number2 = rider_nin = rider_next_of_kin = rider_nok_phonenumber = rider_motorcycle_type = rider_motorcycle_brand = rider_plate_number = rider_bank_name = rider_account_number = rider_account_name = rider_is_verified = ''

        profile_type = ''

        # Buyer profile
        if hasattr(user, 'user_profile') and getattr(user, 'user_profile'):
            up = user.user_profile
            profile_type = profile_type + 'buyer ' if profile_type == '' else profile_type + ', buyer'
            first_name = getattr(up, 'first_name', '') or ''
            last_name = getattr(up, 'last_name', '') or ''
            phone_number = getattr(up, 'phone_number', '') or ''
            gender = getattr(up, 'gender', '') or ''
            dob = getattr(up, 'dob', '') and getattr(up, 'dob').isoformat() or ''
            city = getattr(up, 'city', '') or ''
            state = getattr(up, 'state', '') or ''
            address = getattr(up, 'address', '') or ''
            image = getattr(up, 'image', '') or ''

        # Vendor profile
        if hasattr(user, 'vendor_profile') and getattr(user, 'vendor_profile'):
            vp = user.vendor_profile
            profile_type = profile_type + 'vendor ' if profile_type == '' else profile_type + ', vendor'
            business_name = getattr(vp, 'business_name', '') or ''
            # use property `address` if available, else business_address
            business_address = getattr(vp, 'address', '') or getattr(vp, 'business_address', '') or ''
            business_city = getattr(vp, 'business_location_city', '') or ''
            business_state = getattr(vp, 'business_location_state', '') or ''
            vendor_is_verified = str(getattr(vp, 'is_verified', ''))
            vendor_bank_code = getattr(vp, 'bank_code', '') or ''
            vendor_account_number = getattr(vp, 'account_number', '') or ''
            vendor_plan_type = getattr(vp, 'plan_type', '') or ''

        # Rider profile
        if hasattr(user, 'rider_profile') and getattr(user, 'rider_profile'):
            rp = user.rider_profile
            profile_type = profile_type + 'rider ' if profile_type == '' else profile_type + ', rider'
            rider_phone_number2 = getattr(rp, 'phone_number2', '') or ''
            rider_nin = getattr(rp, 'nin', '') or ''
            rider_next_of_kin = getattr(rp, 'next_of_kin', '') or ''
            rider_nok_phonenumber = getattr(rp, 'nok_phonenumber', '') or ''
            rider_motorcycle_type = getattr(rp, 'motorcycle_type', '') or ''
            rider_motorcycle_brand = getattr(rp, 'motorcycle_brand', '') or ''
            rider_plate_number = getattr(rp, 'plate_number', '') or ''
            rider_bank_name = getattr(rp, 'bank_name', '') or ''
            rider_account_number = getattr(rp, 'account_number', '') or ''
            rider_account_name = getattr(rp, 'account_name', '') or ''
            rider_is_verified = str(getattr(rp, 'is_verified', ''))

        row = [
            user.email,
            roles,
            profile_type.strip(),
            first_name,
            last_name,
            phone_number,
            gender,
            dob,
            city,
            state,
            address,
            image,
            business_name,
            business_address,
            business_city,
            business_state,
            vendor_is_verified,
            vendor_bank_code,
            vendor_account_number,
            vendor_plan_type,
            rider_phone_number2,
            rider_nin,
            rider_next_of_kin,
            rider_nok_phonenumber,
            rider_motorcycle_type,
            rider_motorcycle_brand,
            rider_plate_number,
            rider_bank_name,
            rider_account_number,
            rider_account_name,
            rider_is_verified,
        ]

        writer.writerow(row)

    return response


export_users_csv.short_description = 'Export selected users to CSV (includes profiles)'


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role)

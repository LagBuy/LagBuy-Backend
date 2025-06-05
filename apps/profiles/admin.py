from django.contrib import admin

from .models import UsersProfile, RidersProfile, VendorsProfile

admin.site.register(UsersProfile)
admin.site.register(RidersProfile)
admin.site.register(VendorsProfile)

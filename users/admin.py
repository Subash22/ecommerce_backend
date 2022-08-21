from django.apps import AppConfig
from django.contrib import admin
from .models import *


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'id']

    class Meta:
        model = Profile

admin.site.register(Profile, ProfileAdmin)
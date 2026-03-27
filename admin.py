from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'role',
        'is_email_verified',
        'is_active',
        'is_staff',
        'is_superuser',
    )

    list_filter = (
        'role',
        'is_email_verified',
        'is_active',
    )

    search_fields = (
        'username',
        'email',
    )

    ordering = ('-date_joined',)

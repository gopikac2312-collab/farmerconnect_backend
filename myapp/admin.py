from django.contrib import admin
from .models import User, Product, Farmer

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "role", "is_staff", "is_active")
    search_fields = ("username", "email")
    list_filter = ("role", "is_active")
    ordering = ("id",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'stock', 'is_active', 'is_approved', 'farmer')
    list_filter = ('is_active', 'is_approved', 'farmer')
    search_fields = ('name', 'farmer__user__username')  # optional, for search
    ordering = ('-created_at',)


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "farm_name")
    search_fields = ("user__username", "farm_name")
    ordering = ("id",)






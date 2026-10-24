from django.contrib import admin

from apps.businesses.infrastructure.models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name_en", "slug", "timezone", "default_locale", "is_active")
    list_filter = ("is_active", "default_locale", "timezone")
    search_fields = ("name_en", "name_ar", "slug")
    prepopulated_fields = {"slug": ("name_en",)}

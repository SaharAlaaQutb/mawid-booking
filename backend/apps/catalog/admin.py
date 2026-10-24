from django.contrib import admin

from apps.catalog.infrastructure.models import Service, Staff, StaffService


class StaffServiceInline(admin.TabularInline):
    model = StaffService
    extra = 1
    autocomplete_fields = ("service",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name_en", "business", "duration_minutes", "price_minor", "is_active")
    list_filter = ("business", "is_active")
    search_fields = ("name_en", "name_ar")


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("name_en", "business", "preferred_language", "is_active")
    list_filter = ("business", "is_active", "preferred_language")
    search_fields = ("name_en", "name_ar", "user__email")
    autocomplete_fields = ("user",)
    inlines = (StaffServiceInline,)


@admin.register(StaffService)
class StaffServiceAdmin(admin.ModelAdmin):
    list_display = ("staff", "service")
    list_filter = ("staff__business",)
    autocomplete_fields = ("staff", "service")

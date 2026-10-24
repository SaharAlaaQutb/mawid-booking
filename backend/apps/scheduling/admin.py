from django.contrib import admin

from apps.scheduling.infrastructure.models import TimeOff, WorkingHours


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ("staff", "weekday", "start_time", "end_time")
    list_filter = ("weekday", "staff__business")
    autocomplete_fields = ("staff",)


@admin.register(TimeOff)
class TimeOffAdmin(admin.ModelAdmin):
    list_display = ("staff", "starts_at", "ends_at", "reason")
    list_filter = ("staff__business",)
    search_fields = ("staff__name_en", "staff__name_ar", "reason")
    autocomplete_fields = ("staff", "created_by")

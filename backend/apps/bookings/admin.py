from django.contrib import admin

from apps.bookings.infrastructure.models import Appointment, Customer, Reminder


class ReminderInline(admin.TabularInline):
    model = Reminder
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "business", "language")
    list_filter = ("business", "language")
    search_fields = ("name", "email", "phone")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("starts_at", "staff", "service", "customer", "status", "business")
    list_filter = ("business", "status", "staff")
    search_fields = ("customer__name", "customer__email", "staff__name_en", "service__name_en")
    date_hierarchy = "starts_at"
    autocomplete_fields = ("service", "staff", "customer")
    inlines = (ReminderInline,)


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("appointment", "kind", "send_at", "status", "attempts")
    list_filter = ("status", "kind")
    search_fields = ("appointment__customer__email",)

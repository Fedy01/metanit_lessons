from django.contrib import admin
from .models import MenuCategory, MenuItem, Booking, Table, Restaurant, SocialLink, Setting
from django.contrib import admin

admin.site.site_header = "Zavtraki24 — Панель управления"
admin.site.site_title = "Zavtraki24 Admin"
admin.site.index_title = "Добро пожаловать в Zavtraki24"

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_name', 'order')
    ordering = ('order',)

    def get_name(self, obj):
        return obj.name_i18n.get('ru') or obj.name_i18n.get('en')
    get_name.short_description = "Название (RU)"

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_name', 'price', 'currency', 'available_flag', 'category')
    list_filter = ('available_flag','category')
    search_fields = ('name_i18n', 'description_i18n', 'slug')

    def get_name(self, obj):
        return obj.name_i18n.get('ru') or obj.name_i18n.get('en') or obj.slug
    get_name.short_description = "Название (RU)"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id','customer_name','phone','datetime_from','datetime_to','status','table')
    list_filter = ('status',)
    actions = ['confirm_bookings','cancel_bookings']

    def confirm_bookings(self, request, queryset):
        for b in queryset:
            b.status = Booking.STATUS_CONFIRMED
            b.save()
    confirm_bookings.short_description = "Confirm selected bookings"

    def cancel_bookings(self, request, queryset):
        queryset.update(status=Booking.STATUS_CANCELLED)
    cancel_bookings.short_description = "Cancel selected bookings"

admin.site.register(Table)
admin.site.register(Restaurant)
admin.site.register(SocialLink)
admin.site.register(Setting)
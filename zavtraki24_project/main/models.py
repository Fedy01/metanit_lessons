from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator, RegexValidator, validate_email
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

PHONE_REGEX = RegexValidator(
    regex=r'^\+?\d{7,15}$',
    message=_("Enter a valid phone number, e.g. +375(29)123-22-33")
)

class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=512)
    coords = models.CharField(max_length=64, blank=True, null=True)  # "lat,lon"
    phone = models.CharField(max_length=32, blank=True, null=True)
    working_hours = models.JSONField(blank=True, null=True)  # e.g. {"mon":"9:00-21:00", ...}

    def __str__(self):
        return self.name

class MenuCategory(models.Model):
    order = models.IntegerField(default=0)
    name_i18n = models.JSONField(default=dict)  # {"ru":"Завтраки","en":"Breakfasts"}

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name_i18n.get('ru') or self.name_i18n.get('en') or f"Category {self.pk}"

class MenuItem(models.Model):
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='items')
    name_i18n = models.JSONField(default=dict)
    description_i18n = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(0.01)])
    currency = models.CharField(max_length=8, default='RUB')
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    weight = models.CharField(max_length=64, blank=True, null=True)
    allergens = models.CharField(max_length=255, blank=True, null=True)
    available_flag = models.BooleanField(default=True)
    tags = models.JSONField(default=list, blank=True)  # e.g. ["vegan","gluten-free"]
    slug = models.SlugField(max_length=255, unique=True)

    class Meta:
        ordering = ['category__order', 'name_i18n']

    def __str__(self):
        return (self.name_i18n.get('ru') or self.name_i18n.get('en') or self.slug)

class Table(models.Model):
    name = models.CharField(max_length=100)  # number or name
    seats_count = models.PositiveIntegerField(default=4)
    location_tag = models.CharField(max_length=100, blank=True, null=True)  # e.g. "window"

    def __str__(self):
        return f"{self.name} ({self.seats_count})"

class Booking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_CONFIRMED, _('Confirmed')),
        (STATUS_CANCELLED, _('Cancelled')),
        (STATUS_COMPLETED, _('Completed')),
    ]

    customer_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, validators=[PHONE_REGEX])
    email = models.EmailField(blank=True, null=True)
    datetime_from = models.DateTimeField()
    datetime_to = models.DateTimeField()
    guests_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, related_name='bookings', null=True, blank=True)
    table_preference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-datetime_from']
        indexes = [
            models.Index(fields=['status', 'datetime_from']),
        ]

    def __str__(self):
        return f"Booking {self.customer_name} on {self.datetime_from}"

    @staticmethod
    def get_conflicting_bookings(table, start, end, exclude_booking_id=None):
        qs = Booking.objects.filter(table=table).filter(
            Q(datetime_from__lt=end) & Q(datetime_to__gt=start)
        )
        if exclude_booking_id:
            qs = qs.exclude(pk=exclude_booking_id)
        return qs

    @staticmethod
    def find_available_table(guests_count, start, end, prefer_tag=None):
        # Find tables with enough seats that are not confirmed for the given interval
        tables = Table.objects.filter(seats_count__gte=guests_count)
        if prefer_tag:
            preferred = tables.filter(location_tag__icontains=prefer_tag).order_by('seats_count')
            others = tables.exclude(pk__in=preferred.values_list('pk', flat=True)).order_by('seats_count')
            tables = list(preferred) + list(others)
        for t in tables:
            conflicts = Booking.get_conflicting_bookings(t, start, end)
            # treat pending as reserved? depending on policy — here we check confirmed & pending
            conflicts = conflicts.filter(status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_PENDING])
            if not conflicts.exists():
                return t
        return None

class SocialLink(models.Model):
    platform = models.CharField(max_length=64)
    url = models.URLField()
    icon = models.CharField(max_length=128, blank=True, null=True)  # optional icon name/path
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.platform}"

class Setting(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.key
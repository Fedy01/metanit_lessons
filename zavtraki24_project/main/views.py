from django.shortcuts import render
from rest_framework import serializers, views, status
from rest_framework.response import Response
from django.utils import timezone
from .models import Booking, Table
from django.db import transaction
from datetime import timedelta

class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id","customer_name","phone","email","datetime_from","datetime_to",
            "guests_count","table_preference","note"
        ]

    def validate(self, data):
        start = data['datetime_from']
        end = data['datetime_to']
        if start <= timezone.now():
            raise serializers.ValidationError("datetime_from must be in the future")
        if end <= start:
            raise serializers.ValidationError("datetime_to must be after datetime_from")
        if data['guests_count'] <= 0:
            raise serializers.ValidationError("guests_count must be > 0")
        # limit max duration (e.g., 6 hours)
        if (end - start) > timedelta(hours=6):
            raise serializers.ValidationError("Booking too long")
        return data

class BookingCreateView(views.APIView):
    """
    POST creates a booking. It will try to auto-assign a table.
    """
    serializer_class = BookingCreateSerializer

    def post(self, request, *args, **kwargs):
        ser = self.serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        start = data['datetime_from']
        end = data['datetime_to']
        guests = data['guests_count']
        pref = data.get('table_preference')
        with transaction.atomic():
            table = Booking.find_available_table(guests, start, end, prefer_tag=pref)
            booking = Booking.objects.create(
                customer_name=data['customer_name'],
                phone=data['phone'],
                email=data.get('email'),
                datetime_from=start, datetime_to=end,
                guests_count=guests, table=table,
                table_preference=pref, status=Booking.STATUS_PENDING,
                note=data.get('note','')
            )
            # TODO: enqueue email sending (Celery/Redis) or send sync if simple
        response = {
            "id": booking.id,
            "status": booking.status,
            "assigned_table": booking.table.name if booking.table else None
        }
        return Response(response, status=status.HTTP_201_CREATED)
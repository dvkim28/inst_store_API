from django.contrib.auth import get_user_model
from rest_framework import serializers

from user_service.utils import send_verification_email

from user_service.models import DeliveryAddress


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "password",
            "is_staff",
            "is_email_verified",
            "delivery_address",
            "phone_number",
        ]
        extra_kwargs = {
            "password": {"min_length": 5, "write_only": True},
        }
        read_only_fields = ["id", "is_staff", "is_email_verified"]

    def create(self, validated_data):
        user = get_user_model().objects.create_user(**validated_data)
        send_verification_email(user)
        return user

    def update(self, instance, validated_data):
        user = super().update(instance, validated_data)
        password = validated_data.pop("password", None)
        if password:
            user.set_password(password)
            user.save()
        return user


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ["country", "city", "state", "zip"]


class ManageUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    is_email_verified = serializers.BooleanField(read_only=True)
    delivery_address = DeliveryAddressSerializer()

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_email_verified",
            "phone_number",
            "delivery_address",
        ]

    def update(self, instance, validated_data):
        instance.first_name = (validated_data
                               .get("first_name", instance.first_name))
        instance.last_name = (validated_data
                              .get("last_name", instance.last_name))
        instance.phone_number = validated_data.get(
            "phone_number", instance.phone_number
        )
        delivery_address_data = validated_data.get("delivery_address")
        if delivery_address_data:
            if instance.delivery_address:
                delivery_address = instance.delivery_address
                delivery_address.country = delivery_address_data.get(
                    "country", delivery_address.country
                )
                delivery_address.city = delivery_address_data.get(
                    "city", delivery_address.city
                )
                delivery_address.state = delivery_address_data.get(
                    "state", delivery_address.state
                )
                delivery_address.zip = delivery_address_data.get(
                    "zip", delivery_address.zip
                )
                delivery_address.save()
            else:
                delivery_address = DeliveryAddress.objects.create(
                    **delivery_address_data
                )
                instance.delivery_address = delivery_address

        instance.save()
        return instance

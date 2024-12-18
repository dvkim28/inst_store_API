from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


from user_service.utils import send_verification_email


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "password",
            "is_staff",
            "is_email_verified",
        ]
        extra_kwargs = {
            "password": {"min_length": 5, "max_length": 15, "write_only": True},
        }
        read_only_fields = ["id", "is_staff", "is_email_verified"]

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def create(self, validated_data):
        self.validate_password(validated_data.get("password"))
        user = get_user_model().objects.create_user(**validated_data)
        send_verification_email(user)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        if password:
            self.validate_password(password)
            instance.set_password(password)

        user = super().update(instance, validated_data)
        instance.save()
        return user


class ManageUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    is_email_verified = serializers.BooleanField(read_only=True)
    orders = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_email_verified",
            "orders",
        ]
        read_only_fields = ["id", "is_staff", "is_email_verified"]

    def get_orders(self, obj):
        from store_service.serializers import OrderSerializer

        return OrderSerializer(obj.orders.filter(is_paid=True), many=True).data

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get(
            "first_name",
            instance.first_name)
        instance.last_name = validated_data.get(
            "last_name",
            instance.last_name)
        instance.phone_number = validated_data.get(
            "phone_number",
            instance.phone_number
        )
        instance.save()
        return instance


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            "min_length": "Password must be at least 8 characters long.",
        },
    )
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except serializers.ValidationError:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long"
                " with at least one capital letter and symbol."
            )
        return value

    def validate(self, data):
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        if new_password != confirm_password:
            raise serializers.ValidationError(
                "The two password fields must match."
            )

        return data

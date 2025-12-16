from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    User,
    Classroom,
    Material,
    Enrollment,
    Submission,
    ClassChatMessage,
    DirectChatMessage,
)

UserModel = get_user_model()



# user auth
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ("id", "username", "email", "is_teacher")  # tambah avatar jika ada


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "is_teacher"]

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
            is_teacher=validated_data.get("is_teacher", False),
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


# classroom 
class ClassroomSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    student_count = serializers.IntegerField(source="enrollments.count", read_only=True)

    class Meta:
        model = Classroom
        fields = (
            "id",
            "teacher",
            "title",
            "description",
            "join_token",
            "created_at",
            "student_count",
        )
        read_only_fields = ("join_token",)


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = (
            "id",
            "classroom",
            "title",
            "youtube_url",
            "description",
            "created_at",
        )


class MaterialCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ("id", "title", "youtube_url", "description", "created_at")
        read_only_fields = ("id", "created_at")


# submission enrollment/joined
class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ("id", "user", "classroom", "joined_at")
        read_only_fields = ("joined_at",)


class SubmissionSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = (
            "id",
            "material",
            "student",
            "file",
            "message",
            "created_at",
            "graded",
            "grade",
        )
        read_only_fields = ("student", "created_at")


# chat
class ClassChatMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = ClassChatMessage
        fields = ("id", "material", "sender", "content", "timestamp")


class DirectChatMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)

    class Meta:
        model = DirectChatMessage
        fields = ("id", "sender", "recipient", "content", "timestamp")
        read_only_fields = ("sender", "timestamp")


# list chat summary (sidebar)
class DirectChatSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    last_message = serializers.CharField()
    time = serializers.DateTimeField()


# detail chat dengan user tertentu
class DirectChatRetrieveSerializer(serializers.Serializer):
    user = serializers.DictField()
    messages = DirectChatMessageSerializer(many=True)

import uuid
import secrets
import string
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser


def generate_class_token(lenght = 6):
    letters = string.ascii_uppercase
    return ''.join(secrets.choice(letters) for _ in range(lenght))


class User(AbstractUser):
    username = models.CharField(max_length=150, unique=False)
    email = models.EmailField(unique=True)  # email wajib unik
    is_teacher = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class Classroom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="classrooms"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    join_token = models.CharField(
        max_length=10, unique=True, default=generate_class_token
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def regenerate_token(self):
        self.join_token = generate_class_token()
        self.save()

    def __str__(self):
        return f"{self.title} ({self.teacher})"


class Material(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="materials"
    )
    title = models.CharField(max_length=255)
    youtube_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.classroom.title}"


class Enrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="enrollments"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "classroom")


class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    material = models.ForeignKey(
        Material, on_delete=models.CASCADE, related_name="submissions"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions"
    )
    file = models.FileField(upload_to="submissions/%Y/%m/%d/")
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    graded = models.BooleanField(default=False)
    grade = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]


class ClassChatMessage(models.Model):
    # chat materi
    material = models.ForeignKey(
        Material, on_delete=models.CASCADE, related_name="chat_messages"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


class DirectChatMessage(models.Model):
    # user to user
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_direct_messages",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_direct_messages",
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

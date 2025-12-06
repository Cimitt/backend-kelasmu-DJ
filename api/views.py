from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from .models import Material, Classroom
from .serializers import MaterialCreateSerializer

from .models import (
    Classroom,
    Material,
    Enrollment,
    Submission,
    ClassChatMessage,
    DirectChatMessage,
)
from .serializers import (
    ClassroomSerializer,
    MaterialSerializer,
    EnrollmentSerializer,
    SubmissionSerializer,
    ClassChatMessageSerializer,
    DirectChatMessageSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .permissions import IsTeacher, IsTeacherOrReadOnly

User = get_user_model()


# ===============================
# User / Auth Views
# ===============================
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Endpoint untuk mengambil data user yang sedang login.
        """
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=201)


# ===============================
# Classroom ViewSet
# ===============================
class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]

    def perform_create(self, serializer):
        # Hanya teacher yang dapat membuat kelas
        serializer.save(teacher=self.request.user)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="my-class",
    )
    def my_class(self, request):
        """
        Mengambil semua kelas dimana user adalah teacher / student.
        """
        user = request.user

        # Sebagai teacher
        taught = Classroom.objects.filter(teacher=user)

        # Sebagai student
        enrolled = Classroom.objects.filter(enrollments__user=user)

        # Gabungkan & hilangkan duplikat
        classrooms = (taught | enrolled).distinct()
        serializer = self.get_serializer(classrooms, many=True)
        return Response(serializer.data, status=200)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """
        Join classroom by token.
        """
        classroom = self.get_object()
        token = request.data.get("token")
        if not token:
            return Response({"detail": "token required"}, status=400)
        if token != classroom.join_token:
            return Response({"detail": "invalid token"}, status=400)

        Enrollment.objects.get_or_create(user=request.user, classroom=classroom)
        return Response({"detail": "joined"}, status=200)

    @action(
        detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher]
    )
    def join_by_token(self, request):
        """
        Join classroom via token (teacher only).
        """
        token = request.data.get("token")
        if not token:
            return Response({"detail": "token required"}, status=400)

        classroom = get_object_or_404(Classroom, join_token=token)
        Enrollment.objects.get_or_create(user=request.user, classroom=classroom)
        return Response(
            {"detail": "joined", "classroom": ClassroomSerializer(classroom).data}
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def join_class_by_token(self, request):
        token = request.data.get("token")
        classroom = get_object_or_404(Classroom, join_token=token)
        Enrollment.objects.get_or_create(user=request.user, classroom=classroom)
        return Response(
            {
                "detail": "joined",
                "id": classroom.id,
                "title": classroom.title,
                "teacher": {
                    "id": classroom.teacher.id,
                    "username": classroom.teacher.username,
                },
            }
        )

    @action(
        detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher]
    )
    def regenerate_token(self, request, pk=None):
        """
        Regenerate join token (teacher only).
        """
        classroom = self.get_object()
        if classroom.teacher != request.user:
            return Response({"detail": "not allowed"}, status=403)

        classroom.regenerate_token()
        return Response({"join_token": classroom.join_token})


# ===============================
# Material ViewSet
# ===============================
class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        classroom_id = self.request.query_params.get("classroom")
        if classroom_id:
            qs = qs.filter(classroom_id=classroom_id)
        return qs

    def perform_create(self, serializer):
        classroom = serializer.validated_data.get("classroom")
        if classroom.teacher != self.request.user:
            raise PermissionError("Only classroom teacher can add material")
        serializer.save()


# ===============================
# Submission ViewSet
# ===============================
class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_teacher:
            return qs.filter(material__classroom__teacher=user)
        return qs.filter(student=user)


class CreateMaterialAutoView(generics.CreateAPIView):
    serializer_class = MaterialCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_teacher:
            raise ValidationError("Hanya guru yang dapat membuat materi.")

        # Ambil classroom terbaru milik guru
        classroom = (
            Classroom.objects.filter(teacher=user).order_by("-created_at").first()
        )

        if not classroom:
            raise ValidationError("Anda belum memiliki classroom.")

        serializer.save(classroom=classroom)


# ===============================
# Class Chat ViewSet
# ===============================
class ClassChatMessageViewSet(viewsets.ReadOnlyModelViewSet, mixins.CreateModelMixin):
    queryset = ClassChatMessage.objects.all()
    serializer_class = ClassChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        material_id = self.request.query_params.get("material")
        if material_id:
            qs = qs.filter(material_id=material_id).order_by("timestamp")
        return qs


# chat
class DirectChatViewSet(viewsets.ModelViewSet):
    queryset = DirectChatMessage.objects.all()
    serializer_class = DirectChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def get_queryset(self):
        user = self.request.user
        return DirectChatMessage.objects.filter(
            models.Q(sender=user) | models.Q(recipient=user)
        ).order_by("timestamp")

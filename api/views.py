from rest_framework import viewsets, mixins, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from django.db.models import Q
from django.db import models
from rest_framework.permissions import IsAuthenticated


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
    MaterialCreateSerializer,
    EnrollmentSerializer,
    SubmissionSerializer,
    ClassChatMessageSerializer,
    DirectChatMessageSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .permissions import IsTeacher, IsTeacherOrReadOnly

User = get_user_model()


# auth user
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=201)


# classroom
class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

    @action(detail=False, methods=["get"], url_path="my-class")
    def my_class(self, request):
        user = request.user
        taught = Classroom.objects.filter(teacher=user)
        enrolled = Classroom.objects.filter(enrollments__user=user)
        classrooms = (taught | enrolled).distinct()
        serializer = self.get_serializer(classrooms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        classroom = self.get_object()
        token = request.data.get("token")
        if not token:
            return Response({"detail": "token required"}, status=400)
        if token != classroom.join_token:
            return Response({"detail": "invalid token"}, status=400)

        Enrollment.objects.get_or_create(user=request.user, classroom=classroom)
        return Response({"detail": "joined"}, status=200)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsTeacher])
    def regenerate_token(self, request, pk=None):
        classroom = self.get_object()
        if classroom.teacher != request.user:
            return Response({"detail": "not allowed"}, status=403)
        classroom.regenerate_token()
        return Response({"join_token": classroom.join_token})


# materi
class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        classroom_id = self.request.query_params.get("classroom")
        if classroom_id:
            qs = qs.filter(classroom_id=classroom_id)
        return qs

    def perform_create(self, serializer):
        classroom = serializer.validated_data.get("classroom")
        if classroom.teacher != self.request.user:
            raise ValidationError("Only classroom teacher can add material")
        serializer.save()


class CreateMaterialAutoView(generics.CreateAPIView):
    serializer_class = MaterialCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_teacher:
            raise ValidationError("Hanya guru yang dapat membuat materi.")
        classroom = Classroom.objects.filter(teacher=user).order_by("-created_at").first()
        if not classroom:
            raise ValidationError("Anda belum memiliki classroom.")
        serializer.save(classroom=classroom)


# submission
class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_teacher:
            return qs.filter(material__classroom__teacher=user)
        return qs.filter(student=user)

# chat kelas
class ClassChatMessageViewSet(viewsets.ReadOnlyModelViewSet, mixins.CreateModelMixin):
    queryset = ClassChatMessage.objects.all()
    serializer_class = ClassChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        material_id = self.request.query_params.get("material")
        if material_id:
            qs = qs.filter(material_id=material_id).order_by("timestamp")
        return qs


class DirectChatWithUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        other_user = User.objects.filter(id=user_id).first()
        if not other_user:
            return Response({"detail": "User not found"}, status=404)

        # Ambil semua pesan antara user login dan user lain
        messages = DirectChatMessage.objects.filter(
            Q(sender=request.user, recipient=other_user) |
            Q(sender=other_user, recipient=request.user)
        ).order_by("timestamp")

        serializer = DirectChatMessageSerializer(messages, many=True)
        return Response({
            "user": UserSerializer(other_user).data,
            "messages": serializer.data
        })

# dm
class DirectChatViewSet(viewsets.ModelViewSet):
    serializer_class = DirectChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    # hanya pesan yang berkaitan user yang bisa diakses
    def get_queryset(self):
        user = self.request.user
        return DirectChatMessage.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).order_by("timestamp")

    # sender otomatis diisi saat membuat pesan baru
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    # hanya bisa mengambil pesan yang berkaitan user
    def retrieve(self, request, *args, **kwargs):
        instance = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # search user berdasarkan email
    @action(detail=False, methods=["get"])
    def search_user(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response({"detail": "email query param required"}, status=400)
        users = User.objects.filter(email__iexact=email)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import Classroom, Material, Enrollment, Submission, ClassChatMessage, DirectChatMessage
from .serializers import (
    ClassroomSerializer, MaterialSerializer, EnrollmentSerializer,
    SubmissionSerializer, ClassChatMessageSerializer, DirectChatMessageSerializer,
    RegisterSerializer, UserSerializer
)
from .permissions import IsTeacher, IsTeacherOrReadOnly
from django.contrib.auth import get_user_model

User = get_user_model()

# Register endpoint
from rest_framework.views import APIView
class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(UserSerializer(user).data, status=201)

# Classroom viewset
class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]

    def perform_create(self, serializer):
        # only teacher can create (permission ensures it)
        serializer.save(teacher=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """
        Join classroom by token (or join via token endpoint)
        Alternatively implement `join_by_token` that accepts token.
        """
        classroom = self.get_object()
        token = request.data.get("token")
        if not token:
            return Response({"detail":"token required"}, status=400)
        if token != classroom.join_token:
            return Response({"detail":"invalid token"}, status=400)
        Enrollment.objects.get_or_create(user=request.user, classroom=classroom)
        return Response({"detail":"joined"}, status=200)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher])
    def join_by_token(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail":"token required"}, status=400)
        classroom = get_object_or_404(Classroom, join_token=token)
        Enrollment.objects.get_or_create(user=request.user, classroom=classroom)
        return Response({"detail":"joined", "classroom": ClassroomSerializer(classroom).data})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher])
    def regenerate_token(self, request, pk=None):
        classroom = self.get_object()
        if classroom.teacher != request.user:
            return Response({"detail":"not allowed"}, status=403)
        classroom.regenerate_token()
        return Response({"join_token": classroom.join_token})


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
        # ensure only teacher who owns classroom can create material
        classroom = serializer.validated_data.get("classroom")
        if classroom.teacher != self.request.user:
            raise PermissionError("only classroom teacher can add material")
        serializer.save()

class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        # students see their submissions, teachers see per classroom
        user = self.request.user
        if user.is_teacher:
            # teacher: submissions to their materials
            return qs.filter(material__classroom__teacher=user)
        return qs.filter(student=user)

class ClassChatMessageViewSet(viewsets.ReadOnlyModelViewSet, mixins.CreateModelMixin):
    queryset = ClassChatMessage.objects.all()
    serializer_class = ClassChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def get_queryset(self):
        material_id = self.request.query_params.get("material")
        qs = super().get_queryset()
        if material_id:
            qs = qs.filter(material_id=material_id).order_by("timestamp")
        return qs

class DirectChatViewSet(viewsets.ModelViewSet):
    queryset = DirectChatMessage.objects.all()
    serializer_class = DirectChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def get_queryset(self):
        # return messages where user is participant (either sender or recipient)
        user = self.request.user
        return DirectChatMessage.objects.filter(models.Q(sender=user) | models.Q(recipient=user)).order_by("timestamp")

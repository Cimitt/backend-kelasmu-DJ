from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ClassroomViewSet,
    MaterialViewSet,
    SubmissionViewSet,
    ClassChatMessageViewSet,
    DirectChatViewSet,
    RegisterView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MeView
from .views import CreateMaterialAutoView

router = DefaultRouter()
router.register("classrooms", ClassroomViewSet, basename="classroom")
router.register("materials", MaterialViewSet, basename="material")
router.register("submissions", SubmissionViewSet, basename="submission")
router.register("class-chat", ClassChatMessageViewSet, basename="classchat")
router.register("direct-chat", DirectChatViewSet, basename="directchat")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("users/me/", MeView.as_view(), name="me"),
]

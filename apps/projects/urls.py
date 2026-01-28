from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.projects.views import ProjectViewSet, ProjectMemberViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'members', ProjectMemberViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.projects.views import ProjectViewSet, ProjectMemberViewSet

router = DefaultRouter()
router.register(r'members', ProjectMemberViewSet, basename='projectmember')
router.register(r'', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
]

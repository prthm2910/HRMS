from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.holidays.views import HolidayViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'', HolidayViewSet, basename='holiday')

urlpatterns = [
    path('', include(router.urls)),
]

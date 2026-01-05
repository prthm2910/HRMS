from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeaveRequestViewSet, LeaveBalanceViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()

# 1. Endpoint: /api/leaves/requests/
# (GET list, POST apply, GET detail, PATCH approve/reject)
router.register('requests', LeaveRequestViewSet, basename='leave-request')

# 2. Endpoint: /api/leaves/balance/
# (GET list of remaining leaves)
router.register('balance', LeaveBalanceViewSet, basename='leave-balance')
urlpatterns = [
    path('', include(router.urls)),
]
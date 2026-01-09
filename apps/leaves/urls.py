from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MyLeaveRequestViewSet,
    SubordinateLeaveRequestViewSet,
    LeaveApplyViewSet,
    LeaveBalanceViewSet
)

# Create a router and register our viewsets with it.
router = DefaultRouter()

# 1. Endpoint: /api/leaves/my-requests/
# (GET list of user's own leave requests - read only)
router.register('my-requests', MyLeaveRequestViewSet, basename='my-leave-request')

# 2. Endpoint: /api/leaves/subordinate-requests/
# (GET list of subordinates' leave requests - read only, for managers)
router.register('subordinate-requests', SubordinateLeaveRequestViewSet, basename='subordinate-leave-request')

# 3. Endpoint: /api/leaves/apply/
# (POST to apply for leave, PATCH for managers to approve/reject)
router.register('apply', LeaveApplyViewSet, basename='leave-apply')

# 4. Endpoint: /api/leaves/balance/
# (GET list of remaining leaves)
router.register('balance', LeaveBalanceViewSet, basename='leave-balance')

urlpatterns = [
    path('', include(router.urls)),
]
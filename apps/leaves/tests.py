from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.organization.models import Employee, Department
from apps.leaves.models import LeaveRequest, LeaveBalance, LeaveType
from datetime import date, timedelta

User = get_user_model()

class BulkLeaveApplyTests(APITestCase):
    def setUp(self):
        # 1. Create Department
        self.dept = Department.objects.create(name="Engineering", description="Tech team")

        # 2. Create User and Employee
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            designation="Software Engineer",
            date_of_joining=date.today() - timedelta(days=365),
            salary=50000
        )

        # 3. Setup Leave Balances (These are auto-created by signals, so we just update them)
        lb_casual = LeaveBalance.objects.get(employee=self.employee, leave_type=LeaveType.CASUAL)
        lb_casual.total_allocated = 10.0
        lb_casual.save()

        lb_sick = LeaveBalance.objects.get(employee=self.employee, leave_type=LeaveType.SICK)
        lb_sick.total_allocated = 5.0
        lb_sick.save()

        # 4. Authenticate using force_authenticate (preferred for DRF tests with JWT)
        self.client.force_authenticate(user=self.user)
        self.url = reverse('bulk-leave-list')

    def test_bulk_apply_all_success(self):
        """Test successful submission of multiple valid leave requests."""
        data = {
            "requests": [
                {
                    "leave_type": "CASUAL",
                    "start_date": str(date.today() + timedelta(days=10)),
                    "end_date": str(date.today() + timedelta(days=12)),
                    "reason": "Family vacation"
                },
                {
                    "leave_type": "SICK",
                    "start_date": str(date.today() + timedelta(days=20)),
                    "end_date": str(date.today() + timedelta(days=20)),
                    "reason": "Doctor appointment"
                }
            ]
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['successful']), 2)
        self.assertEqual(len(response.data['failed']), 0)
        self.assertEqual(response.data['summary']['total'], 2)
        self.assertEqual(response.data['summary']['successful'], 2)
        
        # Verify database records
        self.assertEqual(LeaveRequest.objects.filter(employee=self.employee).count(), 2)

    def test_bulk_apply_partial_success(self):
        """Test mixed results when one request is invalid (invalid leave type)."""
        data = {
            "requests": [
                {
                    "leave_type": "CASUAL",
                    "start_date": str(date.today() + timedelta(days=10)),
                    "end_date": str(date.today() + timedelta(days=12)),
                    "reason": "Valid request"
                },
                {
                    "leave_type": "INVALID_TYPE", # This will fail validation
                    "start_date": str(date.today() + timedelta(days=20)),
                    "end_date": str(date.today() + timedelta(days=20)),
                    "reason": "Invalid request"
                }
            ]
        }
        response = self.client.post(self.url, data, format='json')
        
        # Status should be 201 because at least one succeeded
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['successful']), 1)
        self.assertEqual(len(response.data['failed']), 1)
        self.assertEqual(response.data['summary']['successful'], 1)
        self.assertEqual(response.data['summary']['failed'], 1)
        
        # Check error message for failed one
        self.assertIn('leave_type', response.data['failed'][0]['errors'])

    def test_bulk_apply_insufficient_balance(self):
        """Test failure due to insufficient leave balance."""
        data = {
            "requests": [
                {
                    "leave_type": "SICK",
                    "start_date": str(date.today() + timedelta(days=10)),
                    "end_date": str(date.today() + timedelta(days=20)), # 11 days, but only 5 available
                    "reason": "Long sick leave"
                }
            ]
        }
        response = self.client.post(self.url, data, format='json')
        
        # If all requests in the bulk fail, it should return 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        self.assertEqual(len(response.data['successful']), 0)
        self.assertEqual(len(response.data['failed']), 1)
        self.assertIn('non_field_errors', response.data['failed'][0]['errors'])
        self.assertIn('Insufficient Balance', response.data['failed'][0]['errors']['non_field_errors'][0])

    def test_bulk_apply_max_limit(self):
        """Test exceeding the 5-request limit."""
        data = {
            "requests": [
                {"leave_type": "CASUAL", "start_date": "2026-05-01", "end_date": "2026-05-01", "reason": "R"} 
                for _ in range(6) # 6 requests exceeds limit of 5
            ]
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Detailed error will be under 'requests' key in top-level serializer
        self.assertIn('requests', response.data)

    def test_bulk_apply_unauthenticated(self):
        """Test that unauthenticated users cannot access the endpoint."""
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {"requests": []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

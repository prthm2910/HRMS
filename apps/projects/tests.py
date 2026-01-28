from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.organization.models import Employee, Department, HOD
from apps.projects.models import Project, ProjectMember
from apps.audit.models import AuditLog
from datetime import date
from django.db.utils import IntegrityError

User = get_user_model()

class ProjectsRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # --- 1. Setup Data ---
        # Departments
        self.dept_engineering = Department.objects.create(name="Engineering")
        self.dept_hr = Department.objects.create(name="Human Resources")

        # Users & Employees
        # Admin
        self.admin_user = User.objects.create_superuser(username='admin', email='admin@test.com', password='password')
        
        # HOD Engineering
        self.hod_user = User.objects.create_user(username='hod_eng', email='hod_eng@test.com', password='password')
        self.hod_employee = Employee.objects.create(
            user=self.hod_user, department=self.dept_engineering, designation="VP Eng", 
            date_of_joining=date(2020,1,1), salary=100000.00, employee_id="EMP_HOD"
        )
        self.hod_obj = HOD.objects.create(department=self.dept_engineering, employee=self.hod_employee)

        # Regular Engineer (Member of Eng Project)
        self.eng_user = User.objects.create_user(username='dave', email='dave@test.com', password='password')
        self.eng_employee = Employee.objects.create(
            user=self.eng_user, department=self.dept_engineering, designation="Dev", 
            date_of_joining=date(2022,1,1), salary=60000.00, employee_id="EMP_DAVE"
        )

        # HR Employee (Outsider)
        self.hr_user = User.objects.create_user(username='alice', email='alice@test.com', password='password')
        self.hr_employee = Employee.objects.create(
            user=self.hr_user, department=self.dept_hr, designation="Recruiter", 
            date_of_joining=date(2022,1,1), salary=50000.00, employee_id="EMP_ALICE"
        )

        # Projects
        self.eng_project = Project.objects.create(
            name="Backend Squad", department=self.dept_engineering, start_date=date(2024,1,1)
        )
        
        # Memberships
        self.eng_membership = ProjectMember.objects.create(
            project=self.eng_project, employee=self.eng_employee, role="Dev", position="MEMBER",
            date_of_joining=date(2024,1,1)
        )

    # ============================================================================
    # 1. HOD Tests (RBAC & Constraints)
    #    (Note: HOD endpoint is now in /api/organization/)
    # ============================================================================

    def test_hod_unique_constraint(self):
        """Test that a department cannot have two HODs"""
        user2 = User.objects.create_user(username='hod2', email='hod2@test.com', password='password')
        emp2 = Employee.objects.create(
            user=user2, department=self.dept_engineering, designation="Manager",
            date_of_joining=date(2023,1,1), salary=90000.00
        )
        with self.assertRaises(IntegrityError):
            HOD.objects.create(department=self.dept_engineering, employee=emp2)

    def _get_results(self, response):
        """Helper to handle paginated vs non-paginated responses"""
        if isinstance(response.data, dict) and 'results' in response.data:
            return response.data['results']
        return response.data

    def test_rbac_view_hods(self):
        """
        - Admin should see all HODs.
        - HOD should see only themselves.
        - Employee should see nothing (or Forbidden depending on implementation).
        """
        # Admin
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get('/api/organization/hods/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = self._get_results(res)
        self.assertEqual(len(results), 1)

        # HOD
        self.client.force_authenticate(user=self.hod_user)
        res = self.client.get('/api/organization/hods/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = self._get_results(res)
        self.assertEqual(len(results), 1) # Sees self

        # Regular Employee
        self.client.force_authenticate(user=self.eng_user)
        res = self.client.get('/api/organization/hods/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = self._get_results(res)
        self.assertEqual(len(results), 0) # Should filter to empty

        # Ensure Employee cannot Create HOD
        res = self.client.post('/api/organization/hods/', {
            "department": self.dept_hr.id, "employee": self.hr_employee.id
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ============================================================================
    # 2. Project Tests (RBAC & Logic)
    # ============================================================================

    def test_project_visibility_rbac(self):
        """
        - HOD should see only their department's projects.
        - Employee should see only projects they are IN.
        """
        # Create an HR Project (should be invisible to Eng HOD and Eng Employee)
        hr_project = Project.objects.create(name="Recruitment Drive", department=self.dept_hr, start_date=date(2024,1,1))

        # HOD View
        self.client.force_authenticate(user=self.hod_user)
        res = self.client.get('/api/projects/projects/')
        self.assertEqual(res.status_code, 200)
        results = self._get_results(res)
        project_names = [t['name'] for t in results]
        self.assertIn("Backend Squad", project_names)
        self.assertNotIn("Recruitment Drive", project_names)

        # Employee View
        self.client.force_authenticate(user=self.eng_user)
        res = self.client.get('/api/projects/projects/')
        results = self._get_results(res)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Backend Squad")

        # HR Employee (Not in any project yet) View
        self.client.force_authenticate(user=self.hr_user)
        res = self.client.get('/api/projects/projects/')
        results = self._get_results(res)
        self.assertEqual(len(results), 0)

    def test_employee_cannot_create_project(self):
        """A regular employee should NOT be able to create a project."""
        self.client.force_authenticate(user=self.eng_user)
        data = {
            "name": "Rogue Project",
            "start_date": "2024-02-01"
        }
        res = self.client.post('/api/projects/projects/', data)
        # Expected: 403 Forbidden
        self.assertEqual(res.status_code, 403)

    def test_hod_create_project_auto_dept(self):
        """HOD should be able to create a project, and department should be auto-filled."""
        self.client.force_authenticate(user=self.hod_user)
        data = {
            "name": "New Functional Project",
            "start_date": "2024-02-01"
        }
        # Note: We are NOT sending 'department'
        res = self.client.post('/api/projects/projects/', data)
        self.assertEqual(res.status_code, 201)
        
        # Verify Department was auto-filled
        project_id = res.data['id']
        project = Project.objects.get(id=project_id)
        self.assertEqual(project.department, self.dept_engineering)

    # ============================================================================
    # 3. Project Member Tests (Edge Cases)
    # ============================================================================

    def test_add_duplicate_member(self):
        """Cannot add the same employee to the same project twice."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "project": self.eng_project.id,
            "employee": self.eng_employee.id,
            "role": "Duplicate Dev",
            "position": "MEMBER",
            "date_of_joining": "2024-01-02"
        }
        res = self.client.post('/api/projects/members/', data)
        self.assertEqual(res.status_code, 400) # Should be Bad Request due to unique_together

    def test_hod_manage_members_in_own_dept(self):
        """HOD can add members to their own projects."""
        self.client.force_authenticate(user=self.hod_user)
        
        # New employee to add
        new_user = User.objects.create_user(username='intern', email='int@test.com', password='pw')
        new_emp = Employee.objects.create(
            user=new_user, department=self.dept_engineering, designation="Intern",
            date_of_joining=date(2024,6,1), salary=20000.00
        )

        data = {
            "project": self.eng_project.id,
            "employee": new_emp.id,
            "role": "Intern",
            "position": "MEMBER",
            "date_of_joining": "2024-06-01"
        }
        res = self.client.post('/api/projects/members/', data)
        self.assertEqual(res.status_code, 201)

    def test_hod_cannot_manage_other_dept_members(self):
        """HOD cannot add members to another department's project."""
        hr_project = Project.objects.create(name="HR Squad", department=self.dept_hr, start_date=date(2024,1,1))
        
        self.client.force_authenticate(user=self.hod_user)
        data = {
            "project": hr_project.id, # Valid Project ID, but wrong Dept
            "employee": self.eng_employee.id,
            "role": "Spy",
            "position": "MEMBER",
            "date_of_joining": "2024-01-01"
        }
        res = self.client.post('/api/projects/members/', data)
        
        # Should be 400 (Invalid Primary Key relationship / Not Found in filtered queryset)
        # OR 403 Forbidden
        self.assertIn(res.status_code, [400, 403, 404])

    # ============================================================================
    # 4. Soft Delete Tests
    # ============================================================================
    
    def test_soft_delete_project(self):
        """Deleting a project should set is_deleted=True, not remove it."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.delete(f'/api/projects/projects/{self.eng_project.id}/')
        self.assertEqual(res.status_code, 204)
        
        # Check DB
        self.eng_project.refresh_from_db()
        self.assertTrue(self.eng_project.is_deleted)
        self.assertFalse(self.eng_project.is_active)
        
        # Check API visibility
        res = self.client.get(f'/api/projects/projects/{self.eng_project.id}/')
        self.assertEqual(res.status_code, 404)

    def test_hard_delete_project_superuser(self):
        """
        Superuser passing permanent=true should HARD delete the record.
        """
        self.client.force_authenticate(user=self.admin_user)
        # Create a disposable project for this test
        temp_project = Project.objects.create(name="Disposable Project", department=self.dept_engineering, start_date=date(2024,1,1))
        
        # Action: Hard Delete
        res = self.client.delete(f'/api/projects/projects/{temp_project.id}/?permanent=true')
        self.assertEqual(res.status_code, 204)
        
        # Verify it's GONE from DB (not just is_deleted=True)
        self.assertFalse(Project.objects.filter(id=temp_project.id).exists())

    def test_hard_delete_regular_user_fails(self):
        """
        Regular user (even HOD) passing permanent=true should NOT hard delete.
        It should fallback to soft delete (if they have permission) or be forbidden (if they don't).
        """
        # Create a project owned by HOD dept
        temp_project = Project.objects.create(name="HOD Project", department=self.dept_engineering, start_date=date(2024,1,1))
        
        # HOD tries hard delete
        self.client.force_authenticate(user=self.hod_user)
        res = self.client.delete(f'/api/projects/projects/{temp_project.id}/?permanent=true')
        
        # Expectations:
        # Since HOD has permission to delete in their dept, it should succeed at DELETE action
        # BUT it should fail to HARD delete because is_superuser check fails.
        # So specific expectation: 204 No Content (Successful Soft Delete)
        self.assertEqual(res.status_code, 204)
        
        # Verify it is SOFT deleted, not HARD deleted
        # refreshing object might fail if it was hard deleted, so use filter().exists()
        self.assertTrue(Project.objects.filter(id=temp_project.id).exists())
        temp_project.refresh_from_db()
        self.assertTrue(temp_project.is_deleted)

    def test_audit_project_creation(self):
        """
        Test that creating a project creates an AuditLog entry.
        """
        self.client.force_authenticate(user=self.admin_user)
        # 1. Create Project
        res = self.client.post('/api/projects/projects/', {
            "name": "Audit Test Project", 
            "department": self.dept_engineering.id, 
            "start_date": "2024-01-01"
        })
        self.assertEqual(res.status_code, 201)
        project_id = res.data['id']

        # 2. Check Audit Log
        # We expect 1 entry for this table and record ID with action 'CREATE'
        log = AuditLog.objects.filter(table_name="Project", record_id=str(project_id)).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, 'CREATE')


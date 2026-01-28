from rest_framework import serializers
from apps.projects.models import Project, ProjectMember
from apps.base.serializers import BaseTemplateSerializer
from apps.organization.serializers import EmployeeSerializer, DepartmentSerializer

class ProjectMemberSerializer(BaseTemplateSerializer):
    employee_details = EmployeeSerializer(source='employee', read_only=True)

    class Meta:
        model = ProjectMember
        fields = BaseTemplateSerializer.Meta.fields + [
            'project', 'employee', 'employee_details', 'role', 
            'position', 'date_of_joining', 'date_of_leaving'
        ]

    def validate(self, attrs):
        user = self.context['request'].user
        
        # Admin can do anything
        if user.is_superuser:
            return attrs

        # Validate HOD permissions
        # Note: We still check HOD profile because HODs manage projects in their department
        if hasattr(user, 'employee_profile') and hasattr(user.employee_profile, 'hod_profile'):
            hod_dept = user.employee_profile.hod_profile.department
            target_project = attrs.get('project')
            # If creating/updating project assignment
            if target_project and target_project.department != hod_dept:
                raise serializers.ValidationError("You cannot add members to a project in another department.")
        
        return attrs

class ParentProjectSerializer(serializers.ModelSerializer):
    """
    Nested serializer for parent project display.
    Shows name, department details, and project type.
    """
    department_details = DepartmentSerializer(source='department', read_only=True)
    project_type_display = serializers.CharField(source='get_project_type_display', read_only=True)
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'department_details', 'project_type', 'project_type_display']

class ProjectSerializer(BaseTemplateSerializer):
    department_details = DepartmentSerializer(source='department', read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    
    # For write operations: accept department ID
    department = serializers.PrimaryKeyRelatedField(
        queryset=Project.department.field.related_model.objects.all(), 
        required=False,
        write_only=True
    )
    
    # For read operations: show full parent project details
    parent_project_details = ParentProjectSerializer(source='parent_project', read_only=True)
    
    # For write operations: accept parent project ID
    parent_project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        required=False,
        allow_null=True,
        write_only=True
    )
    

    class Meta:
        model = Project
        fields = BaseTemplateSerializer.Meta.fields + [
            'department', 'department_details', 'name', 'description', 
            'project_type', 'start_date', 'end_date', 
            'parent_project', 'parent_project_details', 'members'
        ]
    
    def validate(self, attrs):
        user = self.context['request'].user
        request = self.context.get('request')
        
        # 1. HOD Logic: Auto-fill department, prevent cross-department creation
        if hasattr(user, 'employee_profile') and hasattr(user.employee_profile, 'hod_profile'):
            hod_dept = user.employee_profile.hod_profile.department
            
            # If HOD tries to specify a department
            if 'department' in request.data:
                target_dept = attrs.get('department')
                # Reject if trying to create in another department
                if target_dept and target_dept != hod_dept:
                    raise serializers.ValidationError({
                        "department": f"You can only create projects in your own department ({hod_dept.name}). Department field should not be specified."
                    })
            
            # Always auto-fill with HOD's department
            attrs['department'] = hod_dept
        
        # 2. Admin Logic: Must specify department
        elif user.is_superuser:
            if not attrs.get('department'):
                raise serializers.ValidationError({
                    "department": "This field is required for Administrators. Please specify which department this project belongs to."
                })
        
        # 3. Regular employees cannot create projects (handled by permissions)
        else:
            raise serializers.ValidationError({
                "detail": "Only Administrators and HODs can create projects."
            })
        
        # 4. Duplicate Project Validation
        project_name = attrs.get('name')
        department = attrs.get('department')
        parent_project = attrs.get('parent_project')
        
        if project_name and department:
            # Check for duplicate name within the same department
            duplicate_query = Project.objects.filter(
                name__iexact=project_name,  # Case-insensitive match
                department=department,
                is_deleted=False
            )
            
            # Exclude current instance if updating
            if self.instance:
                duplicate_query = duplicate_query.exclude(id=self.instance.id)
            
            if duplicate_query.exists():
                raise serializers.ValidationError({
                    "name": f"A project with the name '{project_name}' already exists in the {department.name} department."
                })
            
            # Check for duplicate name with the same parent project
            if parent_project:
                duplicate_parent_query = Project.objects.filter(
                    name__iexact=project_name,
                    parent_project=parent_project,
                    is_deleted=False
                )
                
                # Exclude current instance if updating
                if self.instance:
                    duplicate_parent_query = duplicate_parent_query.exclude(id=self.instance.id)
                
                if duplicate_parent_query.exists():
                    raise serializers.ValidationError({
                        "name": f"A project with the name '{project_name}' already exists under the parent project '{parent_project.name}'."
                    })

        return attrs

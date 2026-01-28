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

class ProjectSerializer(BaseTemplateSerializer):
    department_details = DepartmentSerializer(source='department', read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Project.department.field.related_model.objects.all(), 
        required=False
    )

    class Meta:
        model = Project
        fields = BaseTemplateSerializer.Meta.fields + [
            'department', 'department_details', 'name', 'description', 
            'project_type', 'start_date', 'end_date', 'parent_project', 'members'
        ]
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        # 1. HOD Logic
        if hasattr(user, 'employee_profile') and hasattr(user.employee_profile, 'hod_profile'):
            hod_dept = user.employee_profile.hod_profile.department
            target_dept = attrs.get('department')
            
            # If not provided, auto-fill
            if not target_dept:
                attrs['department'] = hod_dept
            # If provided, ensure it matches
            elif target_dept != hod_dept:
                raise serializers.ValidationError({"department": "You cannot create a project in another department."})
        
        # 2. Admin Logic
        elif user.is_superuser:
            if not attrs.get('department'):
                raise serializers.ValidationError({"department": "This field is required for Administrators."})

        return attrs

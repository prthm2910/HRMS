from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Employee, Department

User = get_user_model()

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at']

class EmployeeSerializer(serializers.ModelSerializer):
    # --- READ ONLY (Output) ---
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    mobile_number = serializers.CharField(source='user.phone_number', read_only=True)
    manager_name = serializers.CharField(source='manager.user.get_full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    # --- WRITE ONLY (Input for User Creation) ---
    user_first_name = serializers.CharField(write_only=True, required=False)
    user_last_name = serializers.CharField(write_only=True, required=False)
    user_email = serializers.EmailField(write_only=True, required=True)
    user_password = serializers.CharField(write_only=True, style={'input_type': 'password'}, required=True)
    user_mobile_number = serializers.CharField(write_only=True, required=False)

    # --- RELATIONS (Input) ---
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), 
        source='department',
        write_only=True,
        required=False,
        allow_null=True
    )
    manager_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source='manager',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'created_at', 'updated_at', 'is_active', 'is_deleted',
            
            # User Write Fields
            'user_first_name', 'user_last_name', 'user_email', 'user_password', 'user_mobile_number',
            
            # User Read Fields
            'first_name', 'last_name', 'email', 'mobile_number',
            
            # Relations
            'department_id', 'department_name',
            'manager_id', 'manager_name',
            
            # Job Details
            'designation', 'employment_type', 'salary',
            'date_of_joining', 'date_of_birth',
        ]
        # CRITICAL: employee_id is now strictly read-only
        read_only_fields = ['id', 'employee_id', 'created_at', 'updated_at', 'is_active', 'is_deleted']

    def create(self, validated_data):
        # Extract user data
        u_fname = validated_data.pop('user_first_name', '')
        u_lname = validated_data.pop('user_last_name', '')
        u_email = validated_data.pop('user_email')
        u_password = validated_data.pop('user_password')
        u_phone = validated_data.pop('user_mobile_number', '')

        # Create User
        user = User.objects.create_user(
            username=u_email, 
            email=u_email, 
            password=u_password,
            first_name=u_fname, 
            last_name=u_lname, 
            phone_number=u_phone
        )

        # Create Employee (employee_id generated in models.py save method)
        employee = Employee.objects.create(user=user, **validated_data)
        return employee

    def update(self, instance, validated_data):
        # Handle User updates
        user_fields = ['user_first_name', 'user_last_name', 'user_email', 'user_password', 'user_mobile_number']
        
        if any(field in validated_data for field in user_fields):
            user = instance.user
            if 'user_first_name' in validated_data: user.first_name = validated_data.pop('user_first_name')
            if 'user_last_name' in validated_data: user.last_name = validated_data.pop('user_last_name')
            if 'user_email' in validated_data:
                new_email = validated_data.pop('user_email')
                user.email = new_email
                user.username = new_email 
            if 'user_mobile_number' in validated_data: user.phone_number = validated_data.pop('user_mobile_number')
            if 'user_password' in validated_data:
                pwd = validated_data.pop('user_password')
                if pwd: user.set_password(pwd)
            user.save()

        return super().update(instance, validated_data)
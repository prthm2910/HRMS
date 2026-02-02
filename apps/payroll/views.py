from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.base.views import DeleteMixin, AdminWritePermissionMixin
from apps.payroll.models import (
    SalaryComponent,
    EmployeeSalaryStructure,
    TaxRule,
    PayrollRun,
    Payslip,
    PayslipComponent,
    PayrollAutomationConfig
)
from apps.payroll.serializers import (
    SalaryComponentSerializer,
    EmployeeSalaryStructureSerializer,
    TaxRuleSerializer,
    PayrollRunSerializer,
    PayslipSerializer,
    PayslipDetailSerializer,
    PayslipComponentSerializer,
    PayrollAutomationConfigSerializer
)


class SalaryComponentViewSet(AdminWritePermissionMixin, DeleteMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing salary components (earnings, deductions, bonuses).
    Admin-only for write operations.
    """
    queryset = SalaryComponent.objects.filter(is_deleted=False)
    serializer_class = SalaryComponentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['component_type', 'calculation_method', 'is_taxable']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'component_type', 'created_at']
    ordering = ['component_type', 'name']
    lookup_field = 'code'  # Allow lookup by code instead of ID


class EmployeeSalaryStructureViewSet(AdminWritePermissionMixin, DeleteMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing employee salary structures.
    Admin-only for write operations.
    """
    queryset = EmployeeSalaryStructure.objects.filter(is_deleted=False).select_related(
        'employee', 'salary_component'
    )
    serializer_class = EmployeeSalaryStructureSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'salary_component', 'effective_from']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_id']
    ordering_fields = ['effective_from', 'amount', 'created_at']
    ordering = ['-effective_from']


class TaxRuleViewSet(AdminWritePermissionMixin, DeleteMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing tax rules and slabs.
    Admin-only for write operations.
    """
    queryset = TaxRule.objects.filter(is_deleted=False)
    serializer_class = TaxRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['country', 'is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['country', 'min_income', 'created_at']
    ordering = ['country', 'min_income']
    lookup_field = 'code'  # Allow lookup by code instead of ID


class PayrollRunViewSet(AdminWritePermissionMixin, DeleteMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing payroll runs.
    Admin-only for write operations.
    """
    queryset = PayrollRun.objects.filter(is_deleted=False).select_related('processed_by')
    serializer_class = PayrollRunSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['month', 'year', 'status']
    search_fields = ['code']
    ordering_fields = ['year', 'month', 'created_at']
    ordering = ['-year', '-month']
    lookup_field = 'code'  # Allow lookup by code instead of ID
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def process(self, request, code=None):
        """
        Process payroll for this run.
        TODO: Implement payroll calculation logic
        """
        payroll_run = self.get_object()
        
        if payroll_run.status == PayrollRun.Status.COMPLETED:
            return Response(
                {'error': 'Payroll already processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Implement payroll generation logic here
        # 1. Get all active employees
        # 2. Calculate salary for each employee
        # 3. Create payslips
        # 4. Update totals
        
        return Response({
            'message': 'Payroll processing started',
            'payroll_run_id': str(payroll_run.payroll_run_id)
        })


class PayslipViewSet(DeleteMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing payslips.
    Employees can view their own payslips.
    Admins can view all payslips.
    """
    queryset = Payslip.objects.filter(is_deleted=False).select_related(
        'employee', 'payroll_run'
    ).prefetch_related('components')
    serializer_class = PayslipSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'month', 'year', 'payroll_run']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_id']
    ordering_fields = ['year', 'month', 'created_at']
    ordering = ['-year', '-month']
    
    def get_queryset(self):
        """Filter payslips based on user role"""
        queryset = super().get_queryset()
        
        # Admins see all payslips
        if self.request.user.is_staff or self.request.user.is_superuser:
            return queryset
        
        # Employees see only their own payslips
        try:
            employee = self.request.user.employee_profile
            return queryset.filter(employee=employee)
        except:
            return queryset.none()
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return PayslipDetailSerializer
        return PayslipSerializer
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download payslip PDF.
        TODO: Implement PDF generation
        """
        payslip = self.get_object()
        
        if not payslip.pdf_file:
            return Response(
                {'error': 'PDF not generated yet'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # TODO: Return PDF file response
        return Response({
            'pdf_url': request.build_absolute_uri(payslip.pdf_file.url)
        })


class PayslipComponentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for payslip components.
    """
    queryset = PayslipComponent.objects.filter(is_deleted=False)
    serializer_class = PayslipComponentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['payslip', 'component_type']
    ordering_fields = ['component_type', 'amount']
    ordering = ['component_type', 'component_name']


class PayrollAutomationConfigViewSet(AdminWritePermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for payroll automation configuration.
    Admin-only. Singleton pattern - only one config allowed.
    """
    queryset = PayrollAutomationConfig.objects.filter(is_deleted=False)
    serializer_class = PayrollAutomationConfigSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_object(self):
        """Get or create the singleton config"""
        config, created = PayrollAutomationConfig.objects.get_or_create(
            defaults={'is_enabled': False}
        )
        return config

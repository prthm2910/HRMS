from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.base.views import (
    DeleteMixin,
    AdminWritePermissionMixin,
    BaseAuthenticatedViewSet,
    BaseReadOnlyAuthenticatedViewSet,
    BaseFilteredViewSet
)
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


class SalaryComponentViewSet(AdminWritePermissionMixin, DeleteMixin, BaseFilteredViewSet):
    """
    ViewSet for managing salary components (earnings, deductions, bonuses).
    - Read: All authenticated users
    - Write: Admins only (via AdminWritePermissionMixin)
    """
    queryset = SalaryComponent.objects.filter(is_deleted=False)
    serializer_class = SalaryComponentSerializer
    filterset_fields = ['component_type', 'calculation_method', 'is_taxable']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'component_type', 'created_at']
    ordering = ['component_type', 'name']
    lookup_field = 'code'  # Allow lookup by code instead of ID


class EmployeeSalaryStructureViewSet(AdminWritePermissionMixin, DeleteMixin, BaseFilteredViewSet):
    """
    ViewSet for managing employee salary structures.
    - Read: All authenticated users
    - Write: Admins only (via AdminWritePermissionMixin)
    """
    queryset = EmployeeSalaryStructure.objects.filter(is_deleted=False).select_related(
        'employee', 'salary_component'
    )
    serializer_class = EmployeeSalaryStructureSerializer
    filterset_fields = ['employee', 'salary_component', 'effective_from']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_id']
    ordering_fields = ['effective_from', 'amount', 'created_at']
    ordering = ['-effective_from']


class TaxRuleViewSet(AdminWritePermissionMixin, DeleteMixin, BaseFilteredViewSet):
    """
    ViewSet for managing tax rules and slabs.
    - Read: All authenticated users
    - Write: Admins only (via AdminWritePermissionMixin)
    """
    queryset = TaxRule.objects.filter(is_deleted=False)
    serializer_class = TaxRuleSerializer
    filterset_fields = ['country', 'is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['country', 'min_income', 'created_at']
    ordering = ['country', 'min_income']
    lookup_field = 'code'  # Allow lookup by code instead of ID


class PayrollRunViewSet(AdminWritePermissionMixin, DeleteMixin, BaseFilteredViewSet):
    """
    ViewSet for managing payroll runs.
    - Read: All authenticated users
    - Write: Admins only (via AdminWritePermissionMixin)
    """
    queryset = PayrollRun.objects.filter(is_deleted=False).select_related('processed_by')
    serializer_class = PayrollRunSerializer
    filterset_fields = ['month', 'year', 'status']
    search_fields = ['code']
    ordering_fields = ['year', 'month', 'created_at']
    ordering = ['-year', '-month']
    lookup_field = 'code'  # Allow lookup by code instead of ID
    
    @action(detail=True, methods=['post'])
    def process(self, request, code=None):
        """
        Process payroll for this run.
        Admin-only action (enforced by AdminWritePermissionMixin).
        TODO: Implement payroll calculation logic
        """
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Forbidden: Only Administrators have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
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
    
    @action(detail=True, methods=['post'])
    def send_all_payslips(self, request, code=None):
        """
        Send payslip emails to all employees in this payroll run.
        Admin-only action.
        """
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Forbidden: Only Administrators have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        payroll_run = self.get_object()
        
        try:
            from apps.payroll.services.email_service import send_bulk_payslip_emails
            
            # Send emails
            results = send_bulk_payslip_emails(payroll_run)
            
            return Response({
                'message': 'Bulk email sending completed',
                'total': results['total'],
                'sent': results['sent'],
                'failed': results['failed'],
                'errors': results['errors']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Bulk email sending failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PayslipViewSet(DeleteMixin, BaseFilteredViewSet):
    """
    ViewSet for managing payslips.
    - Employees can view their own payslips
    - Admins can view all payslips
    - Write operations: Admins only (via custom permission check)
    """
    queryset = Payslip.objects.filter(is_deleted=False).select_related(
        'employee', 'payroll_run'
    ).prefetch_related('components')
    serializer_class = PayslipSerializer
    filterset_fields = ['employee', 'month', 'year', 'payroll_run']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_id']
    ordering_fields = ['year', 'month', 'created_at']
    ordering = ['-year', '-month']
    lookup_field = 'payslip_id'  # Use UUID for lookups
    
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
    
    def create(self, request, *args, **kwargs):
        """Only admins can create payslips"""
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Forbidden: Only Administrators have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Only admins can update payslips"""
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Forbidden: Only Administrators have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Only admins can delete payslips"""
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Forbidden: Only Administrators have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def generate_pdf(self, request, payslip_id=None):
        """
        Generate PDF for this payslip.
        Admin-only action.
        """
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Forbidden: Only Administrators have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        payslip = self.get_object()
        
        try:
            # Generate PDF
            pdf_file = payslip.generate_pdf()
            
            return Response({
                'message': 'PDF generated successfully',
                'pdf_url': request.build_absolute_uri(pdf_file.url)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'PDF generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def download(self, request, payslip_id=None):
        """
        Download payslip PDF.
        Employees can download their own payslips, admins can download any.
        """
        from django.http import FileResponse
        
        payslip = self.get_object()
        
        # Check if PDF exists
        if not payslip.pdf_file:
            return Response(
                {'error': 'PDF not generated yet. Please generate PDF first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return PDF file
        try:
            return FileResponse(
                payslip.pdf_file.open('rb'),
                content_type='application/pdf',
                as_attachment=True,
                filename=f"payslip_{payslip.employee.employee_id}_{payslip.year}_{payslip.month:02d}.pdf"
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to download PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def send_email(self, request, payslip_id=None):
        """
        Send payslip via email to employee.
        Admin-only action.
        """
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Forbidden: Only Administrators have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        payslip = self.get_object()
        
        # Check if PDF exists
        if not payslip.pdf_file:
            return Response(
                {'error': 'PDF not generated. Please generate PDF first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.payroll.services.email_service import send_payslip_email
            
            # Send email
            success = send_payslip_email(payslip)
            
            if success:
                return Response({
                    'message': 'Payslip email sent successfully',
                    'sent_to': payslip.employee.user.email,
                    'sent_at': payslip.email_sent_at
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Failed to send email'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': f'Email sending failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class PayslipComponentViewSet(BaseReadOnlyAuthenticatedViewSet):
    """
    Read-only ViewSet for payslip components.
    Uses BaseReadOnlyAuthenticatedViewSet for authenticated read-only access.
    """
    queryset = PayslipComponent.objects.filter(is_deleted=False)
    serializer_class = PayslipComponentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['payslip', 'component_type']
    ordering_fields = ['component_type', 'amount']
    ordering = ['component_type', 'component_name']


class PayrollAutomationConfigViewSet(AdminWritePermissionMixin, BaseAuthenticatedViewSet):
    """
    ViewSet for payroll automation configuration.
    - Read: All authenticated users
    - Write: Admins only (via AdminWritePermissionMixin)
    Singleton pattern - only one config allowed.
    """
    queryset = PayrollAutomationConfig.objects.filter(is_deleted=False)
    serializer_class = PayrollAutomationConfigSerializer
    
    def get_object(self):
        """Get or create the singleton config"""
        config, created = PayrollAutomationConfig.objects.get_or_create(
            defaults={'is_enabled': False}
        )
        return config


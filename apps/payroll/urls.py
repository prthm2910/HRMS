from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.payroll import views

router = DefaultRouter()
router.register(r'salary-components', views.SalaryComponentViewSet, basename='salary-component')
router.register(r'employee-salary-structures', views.EmployeeSalaryStructureViewSet, basename='employee-salary-structure')
router.register(r'tax-rules', views.TaxRuleViewSet, basename='tax-rule')
router.register(r'payroll-runs', views.PayrollRunViewSet, basename='payroll-run')
router.register(r'payslips', views.PayslipViewSet, basename='payslip')
router.register(r'payslip-components', views.PayslipComponentViewSet, basename='payslip-component')
router.register(r'automation-config', views.PayrollAutomationConfigViewSet, basename='automation-config')

urlpatterns = [
    path('', include(router.urls)),
]

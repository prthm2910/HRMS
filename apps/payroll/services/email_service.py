"""
Email Service for Payslip Delivery
Sends payslip PDFs to employees via email
"""

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone


class PayslipEmailService:
    """
    Service for sending payslip emails to employees
    """
    
    def __init__(self, payslip):
        self.payslip = payslip
        self.employee = payslip.employee
        self.user = self.employee.user
        
    def send(self):
        """
        Send payslip email with PDF attachment
        Returns: True if successful, False otherwise
        """
        try:
            # Check if PDF exists
            if not self.payslip.pdf_file:
                raise ValueError("PDF file not generated. Please generate PDF first.")
            
            # Prepare email context
            from apps.base.utils import get_month_name
            
            context = {
                'employee_name': self.user.get_full_name(),
                'month': get_month_name(self.payslip.month),
                'year': self.payslip.year,
                'company_name': getattr(settings, 'COMPANY_NAME', 'Company'),
                'net_salary': self.payslip.net_salary,
            }
            
            # Render email HTML
            html_message = render_to_string('payroll/emails/payslip_email.html', context)
            
            # Create email
            subject = f"Payslip for {context['month']} {context['year']}"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [self.user.email]
            
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=from_email,
                to=recipient_list,
            )
            
            # Set content type to HTML
            email.content_subtype = 'html'
            
            # Attach PDF
            pdf_filename = f"payslip_{self.employee.employee_id}_{self.payslip.year}_{self.payslip.month:02d}.pdf"
            email.attach(pdf_filename, self.payslip.pdf_file.read(), 'application/pdf')
            
            # Send email
            email.send(fail_silently=False)
            
            # Update payslip email status
            self.payslip.email_sent_at = timezone.now()
            self.payslip.save(update_fields=['email_sent_at'])
            
            return True
            
        except Exception as e:
            print(f"Failed to send payslip email: {str(e)}")
            return False


def send_payslip_email(payslip):
    """
    Helper function to send payslip email
    
    Args:
        payslip: Payslip model instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    service = PayslipEmailService(payslip)
    return service.send()


def send_bulk_payslip_emails(payroll_run):
    """
    Send emails for all payslips in a payroll run
    
    Args:
        payroll_run: PayrollRun model instance
        
    Returns:
        dict: Summary of sent/failed emails
    """
    # Optimization: select_related prevents N+1 queries when accessing payslip.employee.user
    payslips = payroll_run.payslips.select_related('employee__user').all()
    
    results = {
        'total': payslips.count(),
        'sent': 0,
        'failed': 0,
        'errors': []
    }
    
    for payslip in payslips:
        try:
            if send_payslip_email(payslip):
                results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Failed to send to {payslip.employee.user.email}")
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"{payslip.employee.user.email}: {str(e)}")
    
    return results

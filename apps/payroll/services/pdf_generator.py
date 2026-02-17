"""
Hybrid PDF Generation Service for Payslips
Combines WeasyPrint (HTML/CSS layout) + ReportLab (security enhancements)
"""

import logging
import qrcode
from io import BytesIO
from datetime import datetime
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML, CSS
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PyPDF2 import PdfReader, PdfWriter


logger = logging.getLogger(__name__)


class HybridPDFGenerator:
    """
    Generates professional payslips using hybrid approach:
    1. WeasyPrint: Base PDF from HTML/CSS template
    2. ReportLab: Add watermark, QR code, security elements
    3. PyPDF2: Merge both layers
    """
    
    def __init__(self, payslip):
        self.payslip = payslip
        self.employee = payslip.employee
        self.payroll_run = payslip.payroll_run
        
    def generate(self) -> bytes:
        """
        Generate complete payslip PDF
        Returns: PDF as bytes
        """
        # Step 1: Generate base PDF with WeasyPrint
        logger.debug(f"Executing Step 1: Base PDF generation (WeasyPrint) | Payslip ID: {self.payslip.payslip_id}")
        base_pdf = self._generate_base_pdf()
        
        # Step 2: Add enhancements with ReportLab
        logger.debug(f"Executing Step 2: Security enhancements (ReportLab) | Payslip ID: {self.payslip.payslip_id}")
        enhanced_pdf = self._add_enhancements(base_pdf)
        
        logger.info(f"Hybrid PDF generation completed | Payslip ID: {self.payslip.payslip_id} | Employee ID: {self.employee.employee_id}")
        return enhanced_pdf
    
    def _generate_base_pdf(self) -> bytes:
        """Generate base PDF using WeasyPrint from HTML template"""
        
        from apps.base.utils import get_month_name
        
        # Prepare context for template
        context = {
            'payslip': self.payslip,
            'employee': self.employee,
            'payroll_run': self.payroll_run,
            'company_name': getattr(settings, 'COMPANY_NAME', 'Company Name'),
            'company_address': getattr(settings, 'COMPANY_ADDRESS', ''),
            'generated_date': datetime.now(),
            'month_name': get_month_name(self.payslip.month),  # Add month name to context
            
            # Salary breakdown
            'earnings': self.payslip.components.filter(
                component_type='EARNING'
            ).order_by('component_name'),
            
            'deductions': self.payslip.components.filter(
                component_type='DEDUCTION'
            ).order_by('component_name'),
            
            'bonuses': self.payslip.components.filter(
                component_type='BONUS'
            ).order_by('component_name'),
        }
        
        # Render HTML template
        html_string = render_to_string('payroll/payslip_template.html', context)
        
        # Generate PDF with WeasyPrint
        pdf_bytes = HTML(string=html_string).write_pdf()
        
        return pdf_bytes
    
    def _add_enhancements(self, base_pdf_bytes: bytes) -> bytes:
        """Add watermark, QR code, and security elements using ReportLab"""
        
        # Read base PDF
        base_pdf = PdfReader(BytesIO(base_pdf_bytes))
        output_pdf = PdfWriter()
        
        # Process each page
        for page_num, page in enumerate(base_pdf.pages):
            # Create overlay with ReportLab
            overlay_bytes = self._create_overlay(page_num)
            overlay_pdf = PdfReader(BytesIO(overlay_bytes))
            
            # Merge overlay with original page
            page.merge_page(overlay_pdf.pages[0])
            output_pdf.add_page(page)
        
        # Write to bytes
        output_stream = BytesIO()
        output_pdf.write(output_stream)
        output_stream.seek(0)
        
        return output_stream.getvalue()
    
    def _create_overlay(self, page_num: int) -> bytes:
        """Create ReportLab overlay with watermark and QR code"""
        
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=A4)
        width, height = A4
        
        # 1. Add watermark
        can.saveState()
        can.setFillColorRGB(0.85, 0.85, 0.85, alpha=0.3)
        can.setFont("Helvetica-Bold", 60)
        can.translate(width / 2, height / 2)
        can.rotate(45)
        can.drawCentredString(0, 0, "CONFIDENTIAL")
        can.restoreState()
        
        # 2. Add QR code for verification (only on first page)
        if page_num == 0:
            qr_data = f"PAYSLIP:{self.payslip.payslip_id}:{self.employee.employee_id}"
            qr_img = self._generate_qr_code(qr_data)
            
            # Position QR code at bottom right
            qr_x = width - 60*mm
            qr_y = 15*mm
            can.drawInlineImage(qr_img, qr_x, qr_y, width=40*mm, height=40*mm)
            
            # Add QR code label
            can.setFont("Helvetica", 8)
            can.setFillColorRGB(0.3, 0.3, 0.3)
            can.drawCentredString(qr_x + 20*mm, qr_y - 5*mm, "Scan to verify")
        
        # 3. Add page numbers
        can.setFont("Helvetica", 9)
        can.setFillColorRGB(0.5, 0.5, 0.5)
        page_text = f"Page {page_num + 1}"
        can.drawRightString(width - 20*mm, 10*mm, page_text)
        
        # 4. Add generation timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        can.setFont("Helvetica", 7)
        can.drawString(20*mm, 10*mm, f"Generated: {timestamp}")
        
        can.save()
        packet.seek(0)
        
        return packet.getvalue()
    
    def _generate_qr_code(self, data: str) -> BytesIO:
        """Generate QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to BytesIO
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes


def generate_payslip_pdf(payslip):
    """
    Main function to generate payslip PDF
    
    Args:
        payslip: Payslip model instance
        
    Returns:
        bytes: PDF file content
    """
    generator = HybridPDFGenerator(payslip)
    return generator.generate()

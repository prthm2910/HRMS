"""
PDF Generation Service for Payslips
"""

import logging
import qrcode
from io import BytesIO
from datetime import datetime

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

logger = logging.getLogger(__name__)


# ── Colour palette (matches HTML template) ─────────────────────────────────
DARK_BLUE   = colors.HexColor('#2c3e50')
MID_BLUE    = colors.HexColor('#34495e')
ACCENT_BLUE = colors.HexColor('#3498db')
LIGHT_GRAY  = colors.HexColor('#ecf0f1')
ROW_ALT     = colors.HexColor('#f9f9f9')
SUMMARY_BG  = colors.HexColor('#e8f4f8')
NET_BG      = colors.HexColor('#d5f4e6')
NET_GREEN   = colors.HexColor('#27ae60')
NOTE_BG     = colors.HexColor('#fff3cd')
NOTE_BORDER = colors.HexColor('#ffc107')
FOOTER_GRAY = colors.HexColor('#666666')
WHITE       = colors.white


# ── Styles ──────────────────────────────────────────────────────────────────
def _build_styles():
    base = getSampleStyleSheet()
    return {
        'company_name': ParagraphStyle(
            'CompanyName',
            fontSize=20, fontName='Helvetica-Bold',
            textColor=DARK_BLUE, alignment=TA_CENTER, spaceAfter=4,
        ),
        'company_address': ParagraphStyle(
            'CompanyAddress',
            fontSize=8, fontName='Helvetica',
            textColor=FOOTER_GRAY, alignment=TA_CENTER,
        ),
        'title': ParagraphStyle(
            'Title',
            fontSize=15, fontName='Helvetica-Bold',
            textColor=MID_BLUE, alignment=TA_CENTER,
            spaceBefore=8, spaceAfter=10,
        ),
        'section': ParagraphStyle(
            'Section',
            fontSize=10, fontName='Helvetica-Bold',
            textColor=DARK_BLUE, spaceBefore=10, spaceAfter=4,
        ),
        'note': ParagraphStyle(
            'Note',
            fontSize=8, fontName='Helvetica',
            textColor=colors.HexColor('#856404'),
            spaceBefore=8, spaceAfter=4,
        ),
        'footer': ParagraphStyle(
            'Footer',
            fontSize=7, fontName='Helvetica',
            textColor=FOOTER_GRAY, alignment=TA_CENTER, spaceAfter=2,
        ),
        'label': ParagraphStyle(
            'Label',
            fontSize=9, fontName='Helvetica-Bold',
            textColor=colors.black,
        ),
        'value': ParagraphStyle(
            'Value',
            fontSize=9, fontName='Helvetica',
            textColor=colors.black,
        ),
    }


# ── Canvas callback for watermark, QR, page numbers ─────────────────────────
class _PageDecorator:
    """Passed as onFirstPage / onLaterPages to SimpleDocTemplate."""

    def __init__(self, payslip):
        self.payslip = payslip
        self._qr_image = None  # generated once, reused

    def _get_qr(self):
        if self._qr_image is None:
            qr_data = f"PAYSLIP:{self.payslip.payslip_id}:{self.payslip.employee.employee_id}"
            qr = qrcode.QRCode(version=1,
                               error_correction=qrcode.constants.ERROR_CORRECT_L,
                               box_size=8, border=2)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            self._qr_image = buf
        else:
            self._qr_image.seek(0)
        return self._qr_image

    def __call__(self, canv, doc):
        width, height = A4
        canv.saveState()

        # 1. Watermark
        canv.setFillColorRGB(0.85, 0.85, 0.85, alpha=0.25)
        canv.setFont("Helvetica-Bold", 55)
        canv.translate(width / 2, height / 2)
        canv.rotate(45)
        canv.drawCentredString(0, 0, "CONFIDENTIAL")
        canv.restoreState()

        canv.saveState()

        # 2. QR code (first page only)
        if doc.page == 1:
            try:
                from reportlab.lib.utils import ImageReader
                qr_buf = self._get_qr()
                qr_size = 30 * mm
                qr_x = width - doc.rightMargin - qr_size
                qr_y = doc.bottomMargin - qr_size - 2 * mm
                canv.drawImage(ImageReader(qr_buf), qr_x, qr_y,
                               width=qr_size, height=qr_size, mask='auto')
                canv.setFont("Helvetica", 6)
                canv.setFillColorRGB(0.3, 0.3, 0.3)
                canv.drawCentredString(qr_x + qr_size / 2, qr_y - 4 * mm, "Scan to verify")
            except Exception:
                logger.warning("QR code rendering failed", exc_info=True)

        # 3. Page number
        canv.setFont("Helvetica", 8)
        canv.setFillColorRGB(0.5, 0.5, 0.5)
        canv.drawRightString(width - doc.rightMargin,
                             doc.bottomMargin - 8 * mm,
                             f"Page {doc.page}")

        # 4. Timestamp (bottom left)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        canv.setFont("Helvetica", 7)
        canv.drawString(doc.leftMargin,
                        doc.bottomMargin - 8 * mm,
                        f"Generated: {timestamp}")

        canv.restoreState()


# ── Info grid (employee details) ─────────────────────────────────────────────
def _info_table(payslip, month_name, styles):
    employee = payslip.employee
    payroll_run = payslip.payroll_run

    try:
        dept = employee.department.name if employee.department else '—'
    except Exception:
        dept = '—'

    payment_date = (
        payroll_run.processed_at.strftime('%d %b %Y')
        if payroll_run.processed_at else '—'
    )

    rows = [
        ('Employee Name',  employee.user.get_full_name() or '—'),
        ('Employee ID',    employee.employee_id or '—'),
        ('Department',     dept),
        ('Designation',    getattr(employee, 'designation', '—') or '—'),
        ('Pay Period',     f"{month_name} {payslip.year}"),
        ('Payment Date',   payment_date),
    ]

    table_data = [
        [
            Paragraph(label, styles['label']),
            Paragraph(value, styles['value']),
        ]
        for label, value in rows
    ]

    col_w = [55 * mm, 105 * mm]
    t = Table(table_data, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('ROWBACKGROUNDS', (1, 0), (1, -1), [WHITE, ROW_ALT]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


# ── Generic salary component table ───────────────────────────────────────────
def _salary_table(components, gross_label=None, gross_amount=None,
                  total_label=None, total_amount=None):
    header = [
        Paragraph('<b>Component</b>', ParagraphStyle(
            'TH', fontSize=9, fontName='Helvetica-Bold', textColor=WHITE)),
        Paragraph('<b>Amount (₹)</b>', ParagraphStyle(
            'THR', fontSize=9, fontName='Helvetica-Bold',
            textColor=WHITE, alignment=TA_RIGHT)),
    ]
    data = [header]

    for i, comp in enumerate(components):
        data.append([
            Paragraph(str(comp.component_name), ParagraphStyle(
                'TD', fontSize=9, fontName='Helvetica')),
            Paragraph(f"{comp.amount:,.2f}", ParagraphStyle(
                'TDR', fontSize=9, fontName='Courier',
                alignment=TA_RIGHT)),
        ])

    # Summary row (Gross / Total)
    if gross_label:
        data.append([
            Paragraph(f'<b>{gross_label}</b>', ParagraphStyle(
                'SR', fontSize=9, fontName='Helvetica-Bold')),
            Paragraph(f'<b>{gross_amount:,.2f}</b>', ParagraphStyle(
                'SRR', fontSize=9, fontName='Courier-Bold',
                alignment=TA_RIGHT)),
        ])
    if total_label:
        data.append([
            Paragraph(f'<b>{total_label}</b>', ParagraphStyle(
                'SR', fontSize=9, fontName='Helvetica-Bold')),
            Paragraph(f'<b>{total_amount:,.2f}</b>', ParagraphStyle(
                'SRR', fontSize=9, fontName='Courier-Bold',
                alignment=TA_RIGHT)),
        ])

    col_w = [120 * mm, 40 * mm]
    t = Table(data, colWidths=col_w)

    style = [
        # Header row
        ('BACKGROUND',   (0, 0), (-1, 0), MID_BLUE),
        ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('PADDING',      (0, 0), (-1, -1), 6),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        # Alternating rows (skip header row 0)
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, ROW_ALT]),
    ]

    # Colour summary/total row
    if gross_label or total_label:
        style += [
            ('BACKGROUND',  (0, -1), (-1, -1), SUMMARY_BG),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, ROW_ALT]),
        ]

    t.setStyle(TableStyle(style))
    return t


def _net_salary_table(net_salary):
    data = [[
        Paragraph('<b>NET SALARY</b>', ParagraphStyle(
            'NS', fontSize=11, fontName='Helvetica-Bold', textColor=NET_GREEN)),
        Paragraph(f'<b>₹ {net_salary:,.2f}</b>', ParagraphStyle(
            'NSR', fontSize=11, fontName='Courier-Bold',
            textColor=NET_GREEN, alignment=TA_RIGHT)),
    ]]
    col_w = [120 * mm, 40 * mm]
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NET_BG),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('PADDING',    (0, 0), (-1, -1), 8),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


# ── Main generator ────────────────────────────────────────────────────────────
class PayslipPDFGenerator:
    """
    Pure ReportLab payslip generator.
    Produces a professional A4 PDF with:
      - Company header
      - Employee info grid
      - Earnings / Bonuses / Deductions tables
      - Net salary row
      - Confidential watermark + QR code via canvas callbacks
    """

    def __init__(self, payslip):
        self.payslip = payslip
        self.employee = payslip.employee
        self.payroll_run = payslip.payroll_run

    def generate(self) -> bytes:
        from apps.base.utils import get_month_name

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm, bottomMargin=25 * mm,
        )

        styles = _build_styles()
        decorator = _PageDecorator(self.payslip)
        company_name = getattr(settings, 'COMPANY_NAME', 'Company Name')
        company_address = getattr(settings, 'COMPANY_ADDRESS', '')
        month_name = get_month_name(self.payslip.month)

        # ── Fetch components ──────────────────────────────────────────────
        earnings   = list(self.payslip.components.filter(
            component_type='EARNING').order_by('component_name'))
        deductions = list(self.payslip.components.filter(
            component_type='DEDUCTION').order_by('component_name'))
        bonuses    = list(self.payslip.components.filter(
            component_type='BONUS').order_by('component_name'))

        # ── Build story ───────────────────────────────────────────────────
        story = []

        # -- Header --
        story.append(Paragraph(company_name, styles['company_name']))
        if company_address:
            story.append(Paragraph(company_address, styles['company_address']))
        story.append(HRFlowable(width='100%', thickness=2,
                                color=DARK_BLUE, spaceAfter=4))
        story.append(Paragraph('PAYSLIP', styles['title']))

        # -- Employee info --
        story.append(_info_table(self.payslip, month_name, styles))
        story.append(Spacer(1, 6 * mm))

        # -- Earnings --
        story.append(Paragraph('Earnings', styles['section']))
        story.append(HRFlowable(width='100%', thickness=1.5,
                                color=ACCENT_BLUE, spaceAfter=3))
        story.append(_salary_table(
            earnings,
            gross_label='Gross Salary',
            gross_amount=float(self.payslip.gross_salary),
        ))
        story.append(Spacer(1, 4 * mm))

        # -- Bonuses (optional) --
        if bonuses:
            story.append(Paragraph('Bonuses', styles['section']))
            story.append(HRFlowable(width='100%', thickness=1.5,
                                    color=ACCENT_BLUE, spaceAfter=3))
            story.append(_salary_table(bonuses))
            story.append(Spacer(1, 4 * mm))

        # -- Deductions --
        story.append(Paragraph('Deductions', styles['section']))
        story.append(HRFlowable(width='100%', thickness=1.5,
                                color=ACCENT_BLUE, spaceAfter=3))
        story.append(_salary_table(
            deductions,
            total_label='Total Deductions',
            total_amount=float(self.payslip.total_deductions),
        ))
        story.append(Spacer(1, 4 * mm))

        # -- Net salary --
        story.append(_net_salary_table(float(self.payslip.net_salary)))
        story.append(Spacer(1, 6 * mm))

        # -- Note --
        story.append(KeepTogether([
            Paragraph(
                '<b>Note:</b> This is a computer-generated payslip and does not '
                'require a signature. Please verify the details and report any '
                'discrepancies to the HR department within 7 days.',
                styles['note'],
            ),
        ]))
        story.append(Spacer(1, 6 * mm))

        # -- Footer --
        story.append(HRFlowable(width='100%', thickness=1.5,
                                color=MID_BLUE, spaceAfter=4))
        story.append(Paragraph(
            f"{company_name} | Payroll Department", styles['footer']))
        story.append(Paragraph(
            "This document is confidential and intended solely for the use of "
            "the individual to whom it is addressed.",
            styles['footer'],
        ))

        # ── Build PDF ─────────────────────────────────────────────────────
        doc.build(story, onFirstPage=decorator, onLaterPages=decorator)

        logger.info(
            f"ReportLab PDF generation completed | "
            f"Payslip ID: {self.payslip.payslip_id} | "
            f"Employee ID: {self.employee.employee_id}"
        )

        buf.seek(0)
        return buf.getvalue()


def generate_payslip_pdf(payslip) -> bytes:
    """
    Public entry point — called from Payslip.generate_pdf().

    Args:
        payslip: Payslip model instance
    Returns:
        bytes: PDF file content
    """
    generator = PayslipPDFGenerator(payslip)
    return generator.generate()

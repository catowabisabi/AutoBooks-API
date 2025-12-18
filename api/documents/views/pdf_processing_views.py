"""
PDF Processing Views
====================
Views for generating PDFs with stamps and signatures.
"""
import io
import base64
from decimal import Decimal
from datetime import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.conf import settings

# PDF Generation imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# PDF manipulation for adding stamp/signature
try:
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes


def get_permission_classes():
    """Allow anonymous access in DEBUG mode for development"""
    if settings.DEBUG:
        return [AllowAny]
    return [IsAuthenticated]


class GenerateInvoicePdfView(APIView):
    """
    Generate PDF from invoice data
    POST /api/v1/invoices/generate-pdf/
    """
    permission_classes = get_permission_classes()
    parser_classes = [JSONParser]
    
    @extend_schema(
        tags=['Document Processing'],
        summary='Generate Invoice PDF',
        description='Generate a professional PDF invoice from structured invoice data with optional signature and stamp.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'invoice': {
                        'type': 'object',
                        'properties': {
                            'invoice_number': {'type': 'string'},
                            'date': {'type': 'string'},
                            'due_date': {'type': 'string'},
                            'customer': {'type': 'object'},
                            'company': {'type': 'object'},
                            'items': {'type': 'array'},
                            'subtotal': {'type': 'number'},
                            'tax_amount': {'type': 'number'},
                            'total': {'type': 'number'},
                            'currency': {'type': 'string'},
                        }
                    },
                    'options': {
                        'type': 'object',
                        'properties': {
                            'template': {'type': 'string', 'enum': ['modern', 'classic', 'minimal']},
                            'locale': {'type': 'string'},
                            'signature': {'type': 'object'},
                            'stamp': {'type': 'object'},
                        }
                    }
                }
            }
        },
        responses={
            200: {'type': 'string', 'format': 'binary', 'description': 'PDF file'},
            400: {'description': 'Invalid request data'},
        }
    )
    def post(self, request):
        """Generate a PDF invoice from the provided data"""
        try:
            invoice_data = request.data.get('invoice', {})
            options = request.data.get('options', {})
            
            if not invoice_data:
                return Response(
                    {'error': 'Invoice data is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate PDF
            pdf_buffer = self._generate_invoice_pdf(invoice_data, options)
            
            # Create response
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            invoice_number = invoice_data.get('invoice_number', 'invoice')
            response['Content-Disposition'] = f'attachment; filename="invoice_{invoice_number}.pdf"'
            
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_invoice_pdf(self, invoice_data, options):
        """Generate PDF from invoice data"""
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center
            textColor=colors.HexColor('#1a365d')
        )
        heading_style = ParagraphStyle(
            'InvoiceHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.HexColor('#2d3748')
        )
        normal_style = ParagraphStyle(
            'InvoiceNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=4
        )
        
        elements = []
        
        # Company Header
        company = invoice_data.get('company', {})
        if company.get('name'):
            company_header = Paragraph(f"<b>{company.get('name', '')}</b>", title_style)
            elements.append(company_header)
            if company.get('address'):
                elements.append(Paragraph(company.get('address', ''), normal_style))
            if company.get('email') or company.get('phone'):
                contact_info = []
                if company.get('email'):
                    contact_info.append(company['email'])
                if company.get('phone'):
                    contact_info.append(company['phone'])
                elements.append(Paragraph(' | '.join(contact_info), normal_style))
            elements.append(Spacer(1, 20))
        
        # Invoice Title
        elements.append(Paragraph("INVOICE", title_style))
        elements.append(Spacer(1, 10))
        
        # Invoice Info
        invoice_number = invoice_data.get('invoice_number', 'N/A')
        date = invoice_data.get('date', '')
        due_date = invoice_data.get('due_date', '')
        
        invoice_info = [
            ['Invoice Number:', invoice_number, 'Date:', date],
            ['', '', 'Due Date:', due_date],
        ]
        
        info_table = Table(invoice_info, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        # Bill To
        customer = invoice_data.get('customer', {})
        elements.append(Paragraph("Bill To:", heading_style))
        customer_info = f"<b>{customer.get('name', 'N/A')}</b>"
        if customer.get('address'):
            customer_info += f"<br/>{customer.get('address')}"
        if customer.get('email'):
            customer_info += f"<br/>{customer.get('email')}"
        if customer.get('phone'):
            customer_info += f"<br/>{customer.get('phone')}"
        elements.append(Paragraph(customer_info, normal_style))
        elements.append(Spacer(1, 20))
        
        # Items Table
        elements.append(Paragraph("Items:", heading_style))
        
        currency = invoice_data.get('currency', 'USD')
        currency_symbol = {'USD': '$', 'EUR': '€', 'GBP': '£', 'TWD': 'NT$', 'CNY': '¥'}.get(currency, currency + ' ')
        
        # Table header
        items_data = [['Description', 'Qty', 'Unit Price', 'Amount']]
        
        # Add items
        items = invoice_data.get('items', [])
        for item in items:
            items_data.append([
                item.get('description', ''),
                str(item.get('quantity', 1)),
                f"{currency_symbol}{item.get('unit_price', 0):,.2f}",
                f"{currency_symbol}{item.get('amount', 0):,.2f}",
            ])
        
        items_table = Table(items_data, colWidths=[9*cm, 2*cm, 3*cm, 3*cm])
        items_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            # Body
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 20))
        
        # Totals
        subtotal = invoice_data.get('subtotal', 0)
        tax_amount = invoice_data.get('tax_amount', 0)
        discount = invoice_data.get('discount_amount', 0)
        total = invoice_data.get('total', 0)
        amount_paid = invoice_data.get('amount_paid', 0)
        balance_due = invoice_data.get('balance_due', total - amount_paid)
        
        totals_data = [
            ['Subtotal:', f"{currency_symbol}{subtotal:,.2f}"],
            ['Tax:', f"{currency_symbol}{tax_amount:,.2f}"],
        ]
        if discount:
            totals_data.append(['Discount:', f"-{currency_symbol}{discount:,.2f}"])
        totals_data.append(['Total:', f"{currency_symbol}{total:,.2f}"])
        if amount_paid:
            totals_data.append(['Amount Paid:', f"{currency_symbol}{amount_paid:,.2f}"])
            totals_data.append(['Balance Due:', f"{currency_symbol}{balance_due:,.2f}"])
        
        totals_table = Table(totals_data, colWidths=[13*cm, 4*cm])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 30))
        
        # Notes
        notes = invoice_data.get('notes')
        if notes:
            elements.append(Paragraph("Notes:", heading_style))
            elements.append(Paragraph(notes, normal_style))
            elements.append(Spacer(1, 10))
        
        # Terms
        terms = invoice_data.get('terms')
        if terms:
            elements.append(Paragraph("Terms & Conditions:", heading_style))
            elements.append(Paragraph(terms, normal_style))
            elements.append(Spacer(1, 10))
        
        # Payment Instructions
        payment_instructions = invoice_data.get('payment_instructions')
        if payment_instructions:
            elements.append(Paragraph("Payment Instructions:", heading_style))
            elements.append(Paragraph(payment_instructions, normal_style))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        return buffer


class AddStampToPdfView(APIView):
    """
    Add a stamp image to an existing PDF
    POST /api/v1/documents/add-stamp/
    """
    permission_classes = get_permission_classes()
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        tags=['Document Processing'],
        summary='Add Stamp to PDF',
        description='Add a company stamp image to an existing PDF document.',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'pdf': {'type': 'string', 'format': 'binary', 'description': 'PDF file to stamp'},
                    'stamp_image': {'type': 'string', 'description': 'Base64 encoded stamp image or file'},
                    'position': {'type': 'string', 'enum': ['bottom-left', 'bottom-right', 'center'], 'default': 'bottom-right'},
                }
            }
        },
        responses={
            200: {'type': 'string', 'format': 'binary', 'description': 'Stamped PDF file'},
            400: {'description': 'Invalid request data'},
        }
    )
    def post(self, request):
        """Add a stamp to a PDF document"""
        try:
            pdf_file = request.FILES.get('pdf')
            stamp_data = request.data.get('stamp_image', '')
            position = request.data.get('position', 'bottom-right')
            
            if not pdf_file:
                return Response(
                    {'error': 'PDF file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not stamp_data:
                return Response(
                    {'error': 'Stamp image is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not HAS_PYPDF2:
                return Response(
                    {'error': 'PDF processing library not available'},
                    status=status.HTTP_501_NOT_IMPLEMENTED
                )
            
            # Process stamp image
            stamp_image = self._process_image_data(stamp_data)
            
            # Add stamp to PDF
            output_buffer = self._add_stamp_to_pdf(pdf_file, stamp_image, position)
            
            # Create response
            response = HttpResponse(output_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="stamped_document.pdf"'
            
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _process_image_data(self, image_data):
        """Process base64 image data or file"""
        if hasattr(image_data, 'read'):
            # It's a file
            return io.BytesIO(image_data.read())
        
        # It's base64 data
        if ',' in image_data:
            # Remove data URL prefix
            image_data = image_data.split(',')[1]
        
        return io.BytesIO(base64.b64decode(image_data))
    
    def _add_stamp_to_pdf(self, pdf_file, stamp_image, position):
        """Add stamp image to PDF"""
        # Read the original PDF
        reader = PdfReader(pdf_file)
        writer = PdfWriter()
        
        # Get page dimensions from first page
        first_page = reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)
        
        # Stamp size (adjust as needed)
        stamp_width = 100
        stamp_height = 100
        
        # Calculate position
        positions = {
            'bottom-left': (50, 50),
            'bottom-right': (page_width - stamp_width - 50, 50),
            'center': ((page_width - stamp_width) / 2, (page_height - stamp_height) / 2),
        }
        x, y = positions.get(position, positions['bottom-right'])
        
        # Create stamp overlay
        stamp_buffer = io.BytesIO()
        c = canvas.Canvas(stamp_buffer, pagesize=(page_width, page_height))
        
        # Save stamp image temporarily
        from PIL import Image as PILImage
        stamp_img = PILImage.open(stamp_image)
        stamp_img_buffer = io.BytesIO()
        stamp_img.save(stamp_img_buffer, format='PNG')
        stamp_img_buffer.seek(0)
        
        from reportlab.lib.utils import ImageReader
        stamp_reader = ImageReader(stamp_img_buffer)
        c.drawImage(stamp_reader, x, y, width=stamp_width, height=stamp_height, mask='auto')
        c.save()
        stamp_buffer.seek(0)
        
        # Merge stamp with each page
        stamp_pdf = PdfReader(stamp_buffer)
        stamp_page = stamp_pdf.pages[0]
        
        for page in reader.pages:
            page.merge_page(stamp_page)
            writer.add_page(page)
        
        # Write output
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        
        return output


class AddSignatureToPdfView(APIView):
    """
    Add a signature to an existing PDF
    POST /api/v1/documents/add-signature/
    """
    permission_classes = get_permission_classes()
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        tags=['Document Processing'],
        summary='Add Signature to PDF',
        description='Add a digital signature image to an existing PDF document.',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'pdf': {'type': 'string', 'format': 'binary', 'description': 'PDF file to sign'},
                    'signature_image': {'type': 'string', 'description': 'Base64 encoded signature image'},
                    'signer_name': {'type': 'string', 'description': 'Name of the signer'},
                    'signed_at': {'type': 'string', 'description': 'Signing timestamp'},
                    'title': {'type': 'string', 'description': 'Signer title (optional)'},
                }
            }
        },
        responses={
            200: {'type': 'string', 'format': 'binary', 'description': 'Signed PDF file'},
            400: {'description': 'Invalid request data'},
        }
    )
    def post(self, request):
        """Add a signature to a PDF document"""
        try:
            pdf_file = request.FILES.get('pdf')
            signature_data = request.data.get('signature_image', '')
            signer_name = request.data.get('signer_name', '')
            signed_at = request.data.get('signed_at', datetime.now().isoformat())
            title = request.data.get('title', '')
            
            if not pdf_file:
                return Response(
                    {'error': 'PDF file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not signature_data:
                return Response(
                    {'error': 'Signature image is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not HAS_PYPDF2:
                return Response(
                    {'error': 'PDF processing library not available'},
                    status=status.HTTP_501_NOT_IMPLEMENTED
                )
            
            # Process signature image
            signature_image = self._process_image_data(signature_data)
            
            # Add signature to PDF
            output_buffer = self._add_signature_to_pdf(
                pdf_file, signature_image, signer_name, signed_at, title
            )
            
            # Create response
            response = HttpResponse(output_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="signed_document.pdf"'
            
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _process_image_data(self, image_data):
        """Process base64 image data or file"""
        if hasattr(image_data, 'read'):
            return io.BytesIO(image_data.read())
        
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        return io.BytesIO(base64.b64decode(image_data))
    
    def _add_signature_to_pdf(self, pdf_file, signature_image, signer_name, signed_at, title):
        """Add signature to the last page of PDF"""
        # Read the original PDF
        reader = PdfReader(pdf_file)
        writer = PdfWriter()
        
        # Get last page dimensions
        last_page_index = len(reader.pages) - 1
        last_page = reader.pages[last_page_index]
        page_width = float(last_page.mediabox.width)
        page_height = float(last_page.mediabox.height)
        
        # Signature settings
        sig_width = 150
        sig_height = 50
        x = page_width - sig_width - 50
        y = 100  # Position from bottom
        
        # Create signature overlay
        sig_buffer = io.BytesIO()
        c = canvas.Canvas(sig_buffer, pagesize=(page_width, page_height))
        
        # Draw signature image
        from PIL import Image as PILImage
        sig_img = PILImage.open(signature_image)
        sig_img_buffer = io.BytesIO()
        sig_img.save(sig_img_buffer, format='PNG')
        sig_img_buffer.seek(0)
        
        from reportlab.lib.utils import ImageReader
        sig_reader = ImageReader(sig_img_buffer)
        c.drawImage(sig_reader, x, y + 30, width=sig_width, height=sig_height, mask='auto')
        
        # Draw signature text
        c.setFont("Helvetica", 10)
        c.drawString(x, y + 20, f"Signed by: {signer_name}")
        if title:
            c.drawString(x, y + 8, f"Title: {title}")
        c.setFont("Helvetica", 8)
        c.drawString(x, y - 4, f"Date: {signed_at}")
        
        c.save()
        sig_buffer.seek(0)
        
        # Read signature overlay
        sig_pdf = PdfReader(sig_buffer)
        sig_page = sig_pdf.pages[0]
        
        # Copy all pages, merging signature only on last page
        for i, page in enumerate(reader.pages):
            if i == last_page_index:
                page.merge_page(sig_page)
            writer.add_page(page)
        
        # Write output
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        
        return output

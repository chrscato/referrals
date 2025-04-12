"""
Utility module for converting email files to PDF format.
"""
import os
import email
from pathlib import Path
import logging
from email import policy
from email.parser import BytesParser
import tempfile
import shutil
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import html
import re
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_html(html_content):
    """
    Convert HTML content to PDF-friendly format while preserving basic formatting.
    Returns a list of PDF elements.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    
    # Create custom styles
    bold_style = ParagraphStyle(
        'Bold',
        parent=normal_style,
        fontName='Helvetica-Bold'
    )
    
    italic_style = ParagraphStyle(
        'Italic',
        parent=normal_style,
        fontName='Helvetica-Oblique'
    )
    
    def process_element(element):
        if element.name is None:  # Text node
            text = element.string.strip()
            if text:
                elements.append(Paragraph(text, normal_style))
        
        elif element.name == 'p':
            text = element.get_text().strip()
            if text:
                elements.append(Paragraph(text, normal_style))
                elements.append(Spacer(1, 12))
        
        elif element.name == 'b' or element.name == 'strong':
            text = element.get_text().strip()
            if text:
                elements.append(Paragraph(text, bold_style))
        
        elif element.name == 'i' or element.name == 'em':
            text = element.get_text().strip()
            if text:
                elements.append(Paragraph(text, italic_style))
        
        elif element.name == 'ul':
            items = []
            for li in element.find_all('li', recursive=False):
                items.append(ListItem(Paragraph(li.get_text().strip(), normal_style)))
            elements.append(ListFlowable(items, bulletType='bullet'))
            elements.append(Spacer(1, 12))
        
        elif element.name == 'ol':
            items = []
            for i, li in enumerate(element.find_all('li', recursive=False), 1):
                items.append(ListItem(Paragraph(f"{i}. {li.get_text().strip()}", normal_style)))
            elements.append(ListFlowable(items, bulletType='decimal'))
            elements.append(Spacer(1, 12))
        
        elif element.name == 'a':
            text = element.get_text().strip()
            href = element.get('href', '')
            if text and href:
                elements.append(Paragraph(f'<link href="{href}">{text}</link>', normal_style))
    
    # Process all elements
    for element in soup.children:
        if element.name is not None:  # Skip empty text nodes
            process_element(element)
    
    return elements

def convert_email_to_pdf(email_path, output_dir=None, replace_original=False):
    """
    Convert an email file (.eml) to PDF format.
    
    Args:
        email_path: Path to the email file
        output_dir: Optional directory to save the PDF. If None, saves in same directory as email
        replace_original: If True, replaces the original .eml file with the PDF. If False, keeps both files.
        
    Returns:
        Path to the created PDF file
    """
    email_path = Path(email_path)
    if not email_path.exists():
        raise FileNotFoundError(f"Email file not found: {email_path}")
    
    if output_dir is None:
        output_dir = email_path.parent
    else:
        output_dir = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output PDF path
    pdf_path = output_dir / f"{email_path.stem}.pdf"
    
    try:
        # Read and parse the email
        with open(email_path, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # Create custom style for headers
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading1'],
            fontSize=12,
            spaceAfter=30,
            textColor=colors.HexColor('#2C3E50')
        )
        
        # Build PDF content
        story = []
        
        # Add email headers
        headers = ['From', 'To', 'Subject', 'Date']
        for header in headers:
            if header in msg:
                value = msg[header]
                story.append(Paragraph(f"<b>{header}:</b> {value}", header_style))
        
        story.append(Spacer(1, 20))
        
        # Add email body
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    if isinstance(body, bytes):
                        body = body.decode()
                    story.append(Paragraph(body, normal_style))
                elif part.get_content_type() == "text/html":
                    body = part.get_content()
                    if isinstance(body, bytes):
                        body = body.decode()
                    # Process HTML content with preserved formatting
                    story.extend(clean_html(body))
        else:
            body = msg.get_content()
            if isinstance(body, bytes):
                body = body.decode()
            if msg.get_content_type() == "text/html":
                story.extend(clean_html(body))
            else:
                story.append(Paragraph(body, normal_style))
        
        # Build PDF
        doc.build(story)
        
        # If replace_original is True, replace the original email with the PDF
        if replace_original:
            try:
                # Remove the original email file
                email_path.unlink()
                logger.info(f"Removed original email file: {email_path}")
                
                # Move the PDF to the original email's location
                shutil.move(str(pdf_path), str(email_path.with_suffix('.pdf')))
                pdf_path = email_path.with_suffix('.pdf')
                logger.info(f"Replaced original email with PDF: {pdf_path}")
            except Exception as e:
                logger.error(f"Error replacing original email file: {str(e)}")
                # If replacement fails, at least we still have the PDF
                logger.info(f"PDF was still created at: {pdf_path}")
        
        logger.info(f"Successfully converted {email_path} to PDF: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Error converting email to PDF: {str(e)}")
        raise

def process_email_folder(folder_path, replace_original=False):
    """
    Process all email files in a folder and convert them to PDF.
    
    Args:
        folder_path: Path to the folder containing email files
        replace_original: If True, replaces original .eml files with PDFs. If False, keeps both files.
        
    Returns:
        List of paths to created PDF files
    """
    folder_path = Path(folder_path)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    pdf_files = []
    
    # Process all .eml files in the folder
    for email_file in folder_path.glob("*.eml"):
        try:
            pdf_path = convert_email_to_pdf(email_file, replace_original=replace_original)
            pdf_files.append(pdf_path)
        except Exception as e:
            logger.error(f"Failed to convert {email_file}: {str(e)}")
    
    return pdf_files 
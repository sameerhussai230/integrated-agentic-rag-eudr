import os
import re
import unicodedata
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from datetime import datetime

# --- LAYOUT CONFIGURATION ---
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40  
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

def sanitize_text(text):
    """Replaces special unicode characters with ASCII equivalents."""
    if not text: return ""
    normalized = unicodedata.normalize('NFKD', text)
    ascii_text = "".join([c for c in normalized if not unicodedata.combining(c)])
    replacements = {'ł': 'l', 'Ł': 'L', 'đ': 'd', 'Đ': 'D', 'ø': 'o', 'Ø': 'O'}
    for char, rep in replacements.items():
        ascii_text = ascii_text.replace(char, rep)
    return ascii_text

def get_image_optimized(path, max_width):
    if not os.path.exists(path): return None
    try:
        img = Image(path)
        aspect = img.imageHeight / float(img.imageWidth)
        img.drawWidth = max_width
        img.drawHeight = max_width * aspect
        return img
    except: return None

def format_text_line(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    return sanitize_text(text).encode('latin-1', 'ignore').decode('latin-1')

def create_full_report(output_filename, agent_text, metrics, region_name, sat_date):
    doc = SimpleDocTemplate(
        output_filename, 
        pagesize=A4,
        rightMargin=MARGIN, leftMargin=MARGIN, 
        topMargin=MARGIN, bottomMargin=MARGIN
    )
    styles = getSampleStyleSheet()
    
    # --- ACADEMIC STYLES ---
    title_style = ParagraphStyle(
        'MainTitle', parent=styles['Heading1'], fontSize=22, 
        textColor=colors.HexColor("#003366"), alignment=TA_CENTER, 
        spaceAfter=20, fontName='Helvetica-Bold'
    )
    
    h1_style = ParagraphStyle(
        'H1', parent=styles['Heading2'], fontSize=14, 
        textColor=colors.HexColor("#333333"), spaceBefore=15, 
        spaceAfter=8, fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'], fontSize=11, 
        leading=14, alignment=TA_JUSTIFY, fontName='Times-Roman'
    )
    
    caption_style = ParagraphStyle(
        'Caption', parent=styles['Normal'], fontSize=9, 
        alignment=TA_CENTER, textColor=colors.grey, fontName='Helvetica-Oblique'
    )

    story = []
    
    # 1. TITLE BLOCK
    clean_region = sanitize_text(region_name)
    story.append(Paragraph("EUDR Compliance & Forensic Audit Report", title_style))
    story.append(Paragraph(f"<b>Subject Area:</b> {clean_region}", ParagraphStyle('Sub', parent=body_style, alignment=TA_CENTER)))
    story.append(Spacer(1, 15))
    
    # 2. METADATA
    report_date = datetime.now().strftime('%Y-%m-%d')
    date_data = [
        [f"Report ID: EUDR-{datetime.now().strftime('%H%M%S')}", f"Generated: {report_date}"],
        [f"Satellite Source: Sentinel-2 L2A", f"Acquisition Date: {sat_date}"]
    ]
    t_meta = Table(date_data, colWidths=[CONTENT_WIDTH/2, CONTENT_WIDTH/2])
    t_meta.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'), 
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.darkgrey),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.lightgrey)
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))
    
    # 3. METRICS
    status = metrics.get('status', 'Unknown')
    if "NON-COMPLIANT" in status: 
        status_color = colors.red
        verdict_text = "NON-COMPLIANT"
    elif "HIGH RISK" in status: 
        status_color = colors.orange
        verdict_text = "HIGH RISK"
    else: 
        status_color = colors.green
        verdict_text = "COMPLIANT"

    data = [
        ["Bio-Physical Metric", "Measurement", "Reference Standard"],
        ["Vegetation Cover", f"{metrics.get('vegetation_cover_pct')}%", "Baseline > 0%"],
        ["Composite Stress Index (CSI)", f"{metrics.get('stress_pct')}%", "Max Threshold 20.0%"],
        ["Final Regulatory Verdict", verdict_text, "Regulation (EU) 2023/1115"]
    ]
    
    col_w = CONTENT_WIDTH / 3
    t = Table(data, colWidths=[col_w, col_w, col_w])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f3f3f3")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
        ('TEXTCOLOR', (1, 3), (1, 3), status_color),
        ('FONTNAME', (1, 3), (1, 3), 'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 25))
    
    # 4. IMAGERY
    img1 = get_image_optimized("data/processed/HighRes_Optical.png", CONTENT_WIDTH)
    if img1:
        story.append(KeepTogether([
            Paragraph("Figure 1: Optical RGB Telemetry", h1_style),
            img1, 
            Paragraph("Source: European Space Agency (ESA) Copernicus Program", caption_style)
        ]))
        story.append(Spacer(1, 15))

    img2 = get_image_optimized("data/processed/HighRes_Analysis.png", CONTENT_WIDTH)
    if img2:
        story.append(KeepTogether([
            Paragraph("Figure 2: Spectral Deforestation Analysis", h1_style),
            img2, 
            Paragraph("Classification: Red (Degradation), Green (Healthy Biomass), Blue (Hydrology)", caption_style)
        ]))
        
    story.append(PageBreak())

    # 5. STATEMENT
    story.append(Paragraph("Official Due Diligence Statement", title_style))
    story.append(Spacer(1, 10))
    
    for line in agent_text.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('#'):
            clean_header = format_text_line(line.lstrip('#').strip())
            story.append(Paragraph(clean_header, h1_style))
        elif line.startswith('- ') or line.startswith('* '):
            clean_bullet = format_text_line(line[2:])
            story.append(Paragraph(f"•  {clean_bullet}", body_style))
        else:
            clean_line = format_text_line(line)
            story.append(Paragraph(clean_line, body_style))
        story.append(Spacer(1, 6))

    # 6. REFERENCES
    story.append(Spacer(1, 30))
    story.append(Paragraph("References & Legal Framework", h1_style))
    
    references = [
        "1. Regulation (EU) 2023/1115 of the European Parliament and of the Council of 31 May 2023 on the making available on the Union market and the export from the Union of certain commodities and products associated with deforestation and forest degradation and repealing Regulation (EU) No 995/2010.",
        "2. European Commission Notice C/2025/4524: Guidance Document for Regulation (EU) 2023/1115.",
        "3. Copernicus Sentinel-2 Satellite Data (L2A Product), European Space Agency (ESA)."
    ]
    
    for ref in references:
        story.append(Paragraph(ref, ParagraphStyle(
            'Ref', parent=body_style, fontSize=10, 
            textColor=colors.black, leading=12
        )))
        story.append(Spacer(1, 4))
            
    doc.build(story)
    return output_filename
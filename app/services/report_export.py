"""Enterprise Report Export Services:
1. Single-File Offline Interactive HTML Report (Zero dependencies, runs 100% offline).
2. Executive Data Dictionary PDF Report (ReportLab + Arabic reshaping + Tahoma font).
"""

import io
import os
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional

# --- PDF Generation Dependencies ---
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas as pdf_canvas
    import arabic_reshaper
    from bidi.algorithm import get_display
    PDF_ENABLED = True
except Exception:
    PDF_ENABLED = False


# ---------------------------------------------------------------------------
# Arabic Text Reshaper for PDF
# ---------------------------------------------------------------------------
_FONT_NAME = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"

def _init_pdf_fonts():
    global _FONT_NAME, _FONT_BOLD
    font_paths = [
        ("ArabicFont", r"C:\Windows\Fonts\tahoma.ttf"),
        ("ArabicFontBold", r"C:\Windows\Fonts\tahomabd.ttf"),
    ]
    if os.path.exists(font_paths[0][1]):
        try:
            pdfmetrics.registerFont(TTFont("ArabicFont", font_paths[0][1]))
            _FONT_NAME = "ArabicFont"
            if os.path.exists(font_paths[1][1]):
                pdfmetrics.registerFont(TTFont("ArabicFontBold", font_paths[1][1]))
                _FONT_BOLD = "ArabicFontBold"
            else:
                _FONT_BOLD = "ArabicFont"
        except Exception:
            pass

def _ar(text: str) -> str:
    """Reshape and reorder Arabic text for correct RTL display in ReportLab."""
    if not text:
        return ""
    text_str = str(text)
    if not any("\u0600" <= c <= "\u06FF" for c in text_str):
        return text_str
    try:
        reshaped = arabic_reshaper.reshape(text_str)
        return get_display(reshaped)
    except Exception:
        return text_str


class NumberedCanvas(pdf_canvas.Canvas):
    """Canvas that computes total pages and prints running header/footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Skip cover page
        self.saveState()
        self.setFont(_FONT_NAME, 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 800, 555, 800)
        self.drawString(40, 805, "TESTR ERD Studio Pro • Executive Data Dictionary")
        
        # Footer
        self.line(40, 45, 555, 45)
        self.drawString(40, 32, "Confidential & Proprietary • Database Architecture Documentation")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(555, 32, page_text)
        self.restoreState()


# ---------------------------------------------------------------------------
# 1. Executive PDF Generator (ReportLab)
# ---------------------------------------------------------------------------
def generate_pdf_report(tables_data: Dict[str, Any], fk_list: list,
                        subsystems: Optional[Dict[str, Any]] = None,
                        dialect: str = "oracle", lang: str = "ar") -> bytes:
    """Generate a corporate, publication-ready PDF Data Dictionary."""
    _init_pdf_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46,
        title="Executive Data Dictionary Report",
        author="TESTR ERD Studio Pro"
    )

    styles = getSampleStyleSheet()
    is_ar = (lang == "ar")
    align = 2 if is_ar else 0  # 2 = Right, 0 = Left

    title_style = ParagraphStyle(
        "CoverTitle",
        fontName=_FONT_BOLD,
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#0f172a"),
        alignment=1
    )
    sub_style = ParagraphStyle(
        "CoverSub",
        fontName=_FONT_NAME,
        fontSize=12,
        leading=18,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )
    section_h1 = ParagraphStyle(
        "SectionH1",
        fontName=_FONT_BOLD,
        fontSize=15,
        leading=20,
        textColor=colors.HexColor("#0284c7"),
        alignment=align,
        spaceBefore=14,
        spaceAfter=6
    )
    table_h2 = ParagraphStyle(
        "TableH2",
        fontName=_FONT_BOLD,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        alignment=align,
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        "BodyAr",
        fontName=_FONT_NAME,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
        alignment=align
    )
    th_style = ParagraphStyle(
        "TH",
        fontName=_FONT_BOLD,
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=1
    )
    pk_style = ParagraphStyle(
        "PK",
        fontName=_FONT_BOLD,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#7c3aed"),
        alignment=1
    )

    story = []

    # --- COVER PAGE ---
    story.append(Spacer(1, 40))
    story.append(Paragraph(_ar("تقرير قاموس البيانات المعماري الشامل" if is_ar else "Executive Architecture Data Dictionary"), title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(_ar(f"قاعدة بيانات TESTR • نظام Oracle 21c • تم التوليد في {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                               if is_ar else f"TESTR Database • Oracle 21c Dialect • Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"), sub_style))
    story.append(Spacer(1, 30))

    # Metrics Summary Box
    total_tables = len(tables_data)
    total_cols = sum(len(d.get("columns", [])) for d in tables_data.values())
    total_fks = len(fk_list)
    subsys_count = 8
    if subsystems:
        if isinstance(subsystems, dict) and "subsystems" in subsystems:
            subsys_count = len(subsystems["subsystems"])
        elif isinstance(subsystems, list):
            subsys_count = len(subsystems)

    stat_data = [
        [
            Paragraph(_ar("إجمالي الجداول" if is_ar else "Total Tables"), th_style),
            Paragraph(_ar("إجمالي الحقول" if is_ar else "Total Attributes"), th_style),
            Paragraph(_ar("علاقات الربط (FK)" if is_ar else "Relationships (FK)"), th_style),
            Paragraph(_ar("الأنظمة الفرعية" if is_ar else "Subsystems"), th_style),
        ],
        [
            Paragraph(f"<font size=16><b>{total_tables}</b></font>", ParagraphStyle("C", fontName=_FONT_BOLD, alignment=1, textColor=colors.HexColor("#0284c7"))),
            Paragraph(f"<font size=16><b>{total_cols}</b></font>", ParagraphStyle("C", fontName=_FONT_BOLD, alignment=1, textColor=colors.HexColor("#10b981"))),
            Paragraph(f"<font size=16><b>{total_fks}</b></font>", ParagraphStyle("C", fontName=_FONT_BOLD, alignment=1, textColor=colors.HexColor("#8b5cf6"))),
            Paragraph(f"<font size=16><b>{subsys_count}</b></font>", ParagraphStyle("C", fontName=_FONT_BOLD, alignment=1, textColor=colors.HexColor("#f59e0b"))),
        ]
    ]
    t_stats = Table(stat_data, colWidths=[125, 125, 125, 125])
    t_stats.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_stats)
    story.append(Spacer(1, 30))

    # Architecture Overview Note
    intro_p = (
        "وثيقة معمارية تنفيذية صادرة آلياً من منصة ERD Studio Pro تتضمن الهيكل التوضيحي الشامل لقاعدة البيانات "
        "مع شروحات وتعليقات الحقول (COMMENT ON COLUMN) والقيود المرجعية لضمان جودة وحوكمة البيانات البرمجية."
        if is_ar else
        "Executive architecture document automatically generated by ERD Studio Pro, detailing database schema tables, "
        "attributes, integrity constraints, and documentation comments."
    )
    story.append(Paragraph(_ar(intro_p), body_style))
    story.append(PageBreak())

    # --- SECTION 2: DATA DICTIONARY TABLES ---
    story.append(Paragraph(_ar("فهرس قاموس البيانات المفصل (Detailed Data Dictionary)" if is_ar else "Detailed Data Dictionary"), section_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284c7"), spaceAfter=12))

    for tname in sorted(tables_data.keys()):
        tdata = tables_data[tname]
        pks = set(tdata.get("pks") or [])
        cols = tdata.get("columns", [])
        t_cmt = tdata.get("comment") or tdata.get("description") or ""

        header_text = f"<b>{tname}</b>"
        if t_cmt:
            header_text += f" &nbsp;•&nbsp; <font size=9 color='#64748b'>{t_cmt}</font>"

        t_header_p = Paragraph(_ar(header_text), table_h2)

        # Build column table
        rows = [
            [
                Paragraph(_ar("#"), th_style),
                Paragraph(_ar("اسم الحقل" if is_ar else "Field Name"), th_style),
                Paragraph(_ar("نوع البيانات" if is_ar else "Data Type"), th_style),
                Paragraph(_ar("PK"), th_style),
                Paragraph(_ar("إجباري" if is_ar else "Null?"), th_style),
                Paragraph(_ar("فريد" if is_ar else "Unq"), th_style),
                Paragraph(_ar("الوصف والملاحظات" if is_ar else "Description / Comment"), th_style),
            ]
        ]

        for i, c in enumerate(cols, 1):
            cname = c.get("name", "")
            is_pk = cname in pks
            nullable_txt = "NOT NULL" if not c.get("nullable", True) else "NULL"
            unq_txt = "✓" if c.get("unique") else ""
            comment_txt = c.get("description") or c.get("comment") or "-"
            
            rows.append([
                Paragraph(str(i), body_style),
                Paragraph(f"<b>{cname}</b>", body_style),
                Paragraph(c.get("type", "TEXT"), body_style),
                Paragraph("<b>PK</b>" if is_pk else "", pk_style),
                Paragraph(nullable_txt, body_style),
                Paragraph(unq_txt, body_style),
                Paragraph(_ar(comment_txt), body_style),
            ])

        col_widths = [22, 115, 85, 30, 50, 30, 188]
        col_table = Table(rows, colWidths=col_widths, repeatRows=1)
        col_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        table_block = [t_header_p, col_table, Spacer(1, 14)]
        story.append(KeepTogether(table_block))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 2. Single-File Offline Interactive HTML Report
# ---------------------------------------------------------------------------
def generate_standalone_html_report(tables_data: Dict[str, Any], fk_list: list,
                                    positions: Optional[Dict[str, Any]] = None,
                                    subsystems: Optional[Dict[str, Any]] = None,
                                    theme: str = "dark", lang: str = "ar",
                                    client_svg: Optional[str] = None) -> str:
    """Generate a 100% self-contained, offline interactive HTML report.

    Contains:
    - Embedded full SVG diagram with Pan & Zoom controls.
    - Click-to-focus and table hover highlighting.
    - Client-side search and subsystem filtering.
    - Full Executive Data Dictionary with descriptions and FK links.
    - Native print layout (@media print) for direct browser PDF export.
    """
    is_ar = (lang == "ar")
    positions = positions or {}
    subsystems_data = subsystems or {"subsystems": []}

    # Ensure all tables have positions
    idx = 0
    for t in tables_data:
        if t not in positions:
            col = idx % 5
            row = idx // 5
            positions[t] = {"x": col * 320 + 80, "y": row * 260 + 80, "width": 270, "height": 180}
            idx += 1

    # Format JSON payload safely embedded inside HTML
    schema_payload_json = json.dumps({
        "tablesData": tables_data,
        "fkList": fk_list,
        "positions": positions,
        "subsystems": subsystems_data,
        "theme": theme,
        "lang": lang,
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }, ensure_ascii=False)

    title_text = "تقرير المخطط المعماري التفاعلي • TESTR ERD Studio Pro" if is_ar else "Interactive Architecture Report • TESTR ERD Studio Pro"

    html = f"""<!DOCTYPE html>
<html lang="{lang}" dir="{'rtl' if is_ar else 'ltr'}" data-theme="{theme}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_text}</title>
<style>
:root {{
  --bg: #090d16;
  --bg-card: #111827;
  --bg-card-subtle: #1e293b;
  --border: #334155;
  --border-light: #1e293b;
  --text: #f8fafc;
  --text-muted: #94a3b8;
  --accent: #38bdf8;
  --accent-glow: rgba(56, 189, 248, 0.15);
  --success: #10b981;
  --purple: #8b5cf6;
  --amber: #f59e0b;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Tahoma, Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Consolas, "Courier New", monospace;
}}
[data-theme="light"] {{
  --bg: #f8fafc;
  --bg-card: #ffffff;
  --bg-card-subtle: #f1f5f9;
  --border: #cbd5e1;
  --border-light: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --accent: #0284c7;
  --accent-glow: rgba(2, 132, 199, 0.12);
  --success: #059669;
  --purple: #7c3aed;
  --amber: #d97706;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  overflow-x: hidden;
}}

/* Top Navigation Bar */
.report-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}}
.brand {{
  display: flex;
  align-items: center;
  gap: 12px;
}}
.brand-badge {{
  background: var(--accent-glow);
  color: var(--accent);
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid var(--accent);
}}
.brand-title {{
  font-size: 16px;
  font-weight: 700;
}}
.brand-sub {{
  font-size: 11.5px;
  color: var(--text-muted);
}}
.header-actions {{
  display: flex;
  align-items: center;
  gap: 8px;
}}
.btn {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  transition: all 0.2s;
}}
.btn:hover {{
  background: var(--bg-card-subtle);
  border-color: var(--accent);
}}
.btn.primary {{
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
}}
.btn.primary:hover {{
  filter: brightness(1.1);
}}

/* Layout Container */
.report-container {{
  max-width: 1440px;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}}

/* Stats Summary Cards */
.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}}
.stat-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
}}
.stat-label {{
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
}}
.stat-num {{
  font-size: 26px;
  font-weight: 800;
  margin-top: 4px;
  color: var(--accent);
}}

/* Interactive Canvas Section */
.canvas-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}}
.canvas-toolbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card-subtle);
  flex-wrap: wrap;
  gap: 10px;
}}
.canvas-tools {{
  display: flex;
  align-items: center;
  gap: 6px;
}}
.canvas-viewport {{
  height: 560px;
  position: relative;
  overflow: hidden;
  background: radial-gradient(circle, var(--border-light) 1px, transparent 1px);
  background-size: 24px 24px;
  cursor: grab;
}}
.canvas-viewport:active {{
  cursor: grabbing;
}}
#viewportSvg {{
  width: 100%;
  height: 100%;
  display: block;
}}

/* Filter & Search Bar */
.filter-bar {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  flex-wrap: wrap;
}}
.search-box {{
  flex: 1;
  min-width: 240px;
  position: relative;
}}
.search-input {{
  width: 100%;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  font-size: 13px;
  outline: none;
}}
.search-input:focus {{
  border-color: var(--accent);
}}
.filter-chips {{
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}}
.chip {{
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  border: 1px solid var(--border);
  background: var(--bg-card);
  cursor: pointer;
  transition: all 0.15s;
}}
.chip:hover, .chip.active {{
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
}}

/* Data Dictionary Section */
.dict-section {{
  display: flex;
  flex-direction: column;
  gap: 16px;
}}
.dict-title {{
  font-size: 18px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.table-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.2s;
}}
.table-card:hover, .table-card.highlighted {{
  border-color: var(--accent);
}}
.table-head {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  background: var(--bg-card-subtle);
  border-bottom: 1px solid var(--border);
}}
.table-name {{
  font-size: 15px;
  font-weight: 700;
  font-family: var(--font-mono);
}}
.table-desc {{
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}}
.col-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}}
.col-table th {{
  background: var(--bg-card);
  color: var(--text-muted);
  font-weight: 700;
  text-align: start;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
}}
.col-table td {{
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-light);
}}
.col-table tr:hover {{
  background: var(--bg-card-subtle);
}}
.badge {{
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  font-family: var(--font-mono);
}}
.badge.pk {{ background: rgba(124, 58, 237, 0.18); color: #a78bfa; border: 1px solid #7c3aed; }}
.badge.fk {{ background: rgba(2, 132, 199, 0.18); color: #38bdf8; border: 1px solid #0284c7; }}

/* Print Rules */
@media print {{
  .report-header, .canvas-toolbar, .filter-bar, .canvas-tools, .canvas-viewport {{
    display: none !important;
  }}
  body {{ background: #fff !important; color: #000 !important; }}
  .table-card {{ page-break-inside: avoid; border: 1px solid #ccc !important; margin-bottom: 16px; }}
  .table-head {{ background: #f0f0f0 !important; }}
  .badge.pk {{ color: #000 !important; border: 1px solid #000 !important; }}
}}
</style>
</head>
<body>

<header class="report-header">
  <div class="brand">
    <span class="brand-badge">OFFLINE REPORT</span>
    <div>
      <div class="brand-title">{title_text}</div>
      <div class="brand-sub">{'يعمل 100% بدون إنترنت ولا خادم • تقرير تفاعلي ومعماري شامل' if is_ar else '100% Offline Standalone • Interactive ERD & Architecture Dictionary'}</div>
    </div>
  </div>
  <div class="header-actions">
    <button class="btn" onclick="toggleTheme()" title="تبديل المظهر">🌓 <span id="lblTheme">{'فاتح/داكن' if is_ar else 'Theme'}</span></button>
    <button class="btn primary" onclick="window.print()" title="طباعة أو تصدير PDF">🖨 <span>{'طباعة / PDF' if is_ar else 'Print / PDF'}</span></button>
  </div>
</header>

<div class="report-container">

  <!-- Summary Cards -->
  <div class="stats-grid">
    <div class="stat-card">
      <span class="stat-label">{'إجمالي الجداول' if is_ar else 'Total Tables'}</span>
      <span class="stat-num">{len(tables_data)}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">{'إجمالي الحقول والخصائص' if is_ar else 'Total Attributes'}</span>
      <span class="stat-num">{sum(len(d.get('columns', [])) for d in tables_data.values())}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">{'علاقات المفاتيح الخارجية' if is_ar else 'Foreign Key Relations'}</span>
      <span class="stat-num">{len(fk_list)}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">{'تاريخ التوليد' if is_ar else 'Generated On'}</span>
      <span class="stat-num" style="font-size:16px; margin-top:8px;">{datetime.now().strftime('%Y-%m-%d')}</span>
    </div>
  </div>

  <!-- Interactive SVG Canvas -->
  <div class="canvas-card">
    <div class="canvas-toolbar">
      <div style="font-weight:700; font-size:13px; display:flex; align-items:center; gap:6px;">
        <span>🗺</span>
        <span>{'مخطط الجداول والعلاقات التفاعلي (Interactive Schema Diagram)' if is_ar else 'Interactive ER Diagram'}</span>
      </div>
      <div class="canvas-tools">
        <button class="btn" onclick="zoomIn()" title="تكبير">+</button>
        <button class="btn" onclick="resetZoom()" title="ضبط 1:1">1:1</button>
        <button class="btn" onclick="zoomOut()" title="تصغير">-</button>
        <button class="btn" onclick="fitView()" title="ملاءمة">⛶ {'ملاءمة' if is_ar else 'Fit'}</button>
      </div>
    </div>
    <div class="canvas-viewport" id="viewport">
      <svg id="viewportSvg" viewBox="0 0 2400 1600">
        <g id="scene">
          <g id="relationsGroup"></g>
          <g id="tablesGroup"></g>
        </g>
      </svg>
    </div>
  </div>

  <!-- Search & Filter Controls -->
  <div class="filter-bar">
    <div class="search-box">
      <input type="text" id="searchInput" class="search-input" placeholder="{'بحث فوري في الجداول والحقول والشروحات...' if is_ar else 'Instant search across tables and attributes...'}" oninput="handleSearch(this.value)">
    </div>
    <div class="filter-chips" id="chipsContainer">
      <button class="chip active" onclick="filterSubsystem('all')">{'الكل' if is_ar else 'All'} ({len(tables_data)})</button>
    </div>
  </div>

  <!-- Detailed Data Dictionary -->
  <div class="dict-section">
    <div class="dict-title">
      <span>📖</span>
      <span>{'قاموس البيانات المعماري المفصل (Data Dictionary)' if is_ar else 'Executive Data Dictionary'}</span>
    </div>
    <div id="dictList"></div>
  </div>

</div>

<script>
// --- Embedded Self-Contained Model ---
const MODEL = {schema_payload_json};

let zoom = 0.85;
let panX = 40;
let panY = 40;
let isDragging = false;
let startX = 0, startY = 0;
let activeFilter = 'all';
let highlightedTable = null;

const viewport = document.getElementById('viewport');
const scene = document.getElementById('scene');
const tablesGroup = document.getElementById('tablesGroup');
const relationsGroup = document.getElementById('relationsGroup');
const dictList = document.getElementById('dictList');
const chipsContainer = document.getElementById('chipsContainer');

function updateTransform() {{
  scene.setAttribute('transform', `translate(${{panX}}, ${{panY}}) scale(${{zoom}})`);
}}

function zoomIn() {{ zoom *= 1.2; updateTransform(); }}
function zoomOut() {{ zoom *= 0.8; updateTransform(); }}
function resetZoom() {{ zoom = 1.0; panX = 40; panY = 40; updateTransform(); }}
function fitView() {{
  zoom = 0.75; panX = 60; panY = 40; updateTransform();
}}

viewport.addEventListener('mousedown', e => {{
  if (e.target.closest('.table-node-svg')) return;
  isDragging = true;
  startX = e.clientX - panX;
  startY = e.clientY - panY;
}});
window.addEventListener('mousemove', e => {{
  if (!isDragging) return;
  panX = e.clientX - startX;
  panY = e.clientY - startY;
  updateTransform();
}});
window.addEventListener('mouseup', () => {{ isDragging = false; }});
viewport.addEventListener('wheel', e => {{
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.1 : 0.9;
  zoom *= factor;
  updateTransform();
}}, {{ passive: false }});

function toggleTheme() {{
  const cur = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
}}

// Draw SVG Tables & Relations
function renderDiagram() {{
  tablesGroup.innerHTML = '';
  relationsGroup.innerHTML = '';

  const {{ tablesData, fkList, positions }} = MODEL;

  // Draw Relationships (Orthogonal bezier lines)
  fkList.forEach(f => {{
    const cp = positions[f.child];
    const pp = positions[f.parent];
    if (!cp || !pp) return;
    const x1 = cp.x + 135;
    const y1 = cp.y + 20;
    const x2 = pp.x + 135;
    const y2 = pp.y + 20;

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const dx = Math.abs(x2 - x1) * 0.4;
    const d = `M ${{x1}} ${{y1}} C ${{x1 + (x2 > x1 ? dx : -dx)}} ${{y1}}, ${{x2 - (x2 > x1 ? dx : -dx)}} ${{y2}}, ${{x2}} ${{y2}}`;
    path.setAttribute('d', d);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#64748b');
    path.setAttribute('stroke-width', '1.8');
    path.setAttribute('stroke-dasharray', '4 3');
    path.setAttribute('class', `rel-line rel-${{f.child}} rel-${{f.parent}}`);
    relationsGroup.appendChild(path);
  }});

  // Draw Tables
  Object.keys(tablesData).forEach(tname => {{
    const data = tablesData[tname];
    const pos = positions[tname] || {{ x: 100, y: 100, width: 270, height: 160 }};
    const cols = data.columns || [];
    const pks = data.pks || [];

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'table-node-svg');
    g.setAttribute('id', `svg-node-${{tname}}`);
    g.setAttribute('transform', `translate(${{pos.x}}, ${{pos.y}})`);
    g.style.cursor = 'pointer';
    g.onclick = () => focusTable(tname);

    // Box
    const h = 32 + Math.min(cols.length, 12) * 22;
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('width', 270);
    rect.setAttribute('height', h);
    rect.setAttribute('rx', '8');
    rect.setAttribute('fill', '#111827');
    rect.setAttribute('stroke', '#334155');
    rect.setAttribute('stroke-width', '1.5');
    rect.setAttribute('id', `rect-${{tname}}`);
    g.appendChild(rect);

    // Title Rect
    const titleRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    titleRect.setAttribute('width', 270);
    titleRect.setAttribute('height', '32');
    titleRect.setAttribute('rx', '8');
    titleRect.setAttribute('fill', '#1e293b');
    g.appendChild(titleRect);

    // Title Text
    const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    txt.setAttribute('x', '135');
    txt.setAttribute('y', '20');
    txt.setAttribute('text-anchor', 'middle');
    txt.setAttribute('fill', '#38bdf8');
    txt.setAttribute('font-family', 'ui-monospace, monospace');
    txt.setAttribute('font-size', '12');
    txt.setAttribute('font-weight', 'bold');
    txt.textContent = tname;
    g.appendChild(txt);

    // Columns sample
    cols.slice(0, 10).forEach((col, ci) => {{
      const cy = 48 + ci * 20;
      const isPk = pks.includes(col.name);

      const colTxt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      colTxt.setAttribute('x', '14');
      colTxt.setAttribute('y', cy);
      colTxt.setAttribute('fill', isPk ? '#a78bfa' : '#cbd5e1');
      colTxt.setAttribute('font-size', '11');
      colTxt.setAttribute('font-family', 'ui-monospace, monospace');
      colTxt.textContent = (isPk ? '🔑 ' : '') + col.name;
      g.appendChild(colTxt);

      const typeTxt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      typeTxt.setAttribute('x', '256');
      typeTxt.setAttribute('y', cy);
      typeTxt.setAttribute('text-anchor', 'end');
      typeTxt.setAttribute('fill', '#64748b');
      typeTxt.setAttribute('font-size', '10');
      typeTxt.textContent = col.type || '';
      g.appendChild(typeTxt);
    }});

    tablesGroup.appendChild(g);
  }});
}}

// Focus & Highlight Table
function focusTable(tname) {{
  highlightedTable = tname;
  document.querySelectorAll('.table-card').forEach(c => c.classList.remove('highlighted'));
  const card = document.getElementById(`card-${{tname}}`);
  if (card) {{
    card.classList.add('highlighted');
    card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
  }}

  // Highlight in SVG
  document.querySelectorAll('.table-node-svg rect').forEach(r => r.setAttribute('stroke', '#334155'));
  const r = document.getElementById(`rect-${{tname}}`);
  if (r) r.setAttribute('stroke', '#38bdf8');
}}

// Render Data Dictionary Cards
function renderDictionary() {{
  dictList.innerHTML = '';
  const {{ tablesData, fkList }} = MODEL;

  Object.keys(tablesData).sort().forEach(tname => {{
    const data = tablesData[tname];
    const pks = data.pks || [];
    const cols = data.columns || [];
    const tCmt = data.comment || data.description || '';

    const card = document.createElement('div');
    card.className = 'table-card';
    card.id = `card-${{tname}}`;

    let rowsHtml = cols.map((col, i) => {{
      const isPk = pks.includes(col.name);
      const isFk = fkList.some(f => f.child === tname && (f.cols || '').toLowerCase() === col.name.toLowerCase());
      const cmt = col.description || col.comment || '-';
      return `<tr>
        <td style="color:var(--text-muted);">${{i+1}}</td>
        <td><b>${{col.name}}</b></td>
        <td style="font-family:var(--font-mono); color:var(--accent);">${{col.type}}</td>
        <td>${{isPk ? '<span class="badge pk">PK</span>' : ''}} ${{isFk ? '<span class="badge fk">FK</span>' : ''}}</td>
        <td>${{col.nullable === false ? 'NOT NULL' : 'NULL'}}</td>
        <td>${{col.unique ? '✓' : '-'}}</td>
        <td>${{cmt}}</td>
      </tr>`;
    }}).join('');

    card.innerHTML = `
      <div class="table-head">
        <div>
          <div class="table-name">${{tname}}</div>
          <div class="table-desc">${{tCmt || 'جدول في قاعدة البيانات'}}</div>
        </div>
        <button class="btn" onclick="focusTable('${{tname}}')">🔍 تركيز</button>
      </div>
      <table class="col-table">
        <thead>
          <tr>
            <th>#</th>
            <th>{'اسم الحقل' if is_ar else 'Field Name'}</th>
            <th>{'النوع' if is_ar else 'Type'}</th>
            <th>{'المفاتيح' if is_ar else 'Keys'}</th>
            <th>{'الإلزامية' if is_ar else 'Nullable'}</th>
            <th>{'فريد' if is_ar else 'Unique'}</th>
            <th>{'الشرح والوصف' if is_ar else 'Description'}</th>
          </tr>
        </thead>
        <tbody>
          ${{rowsHtml}}
        </tbody>
      </table>
    `;
    dictList.appendChild(card);
  }});
}}

// Render Subsystems Chips
function renderSubsystemChips() {{
  const subs = (MODEL.subsystems && MODEL.subsystems.subsystems) ? MODEL.subsystems.subsystems : [];
  const mapping = (MODEL.subsystems && MODEL.subsystems.mapping) ? MODEL.subsystems.mapping : {{}};
  if (!subs || !subs.length) return;
  subs.forEach(s => {{
    const btn = document.createElement('button');
    btn.className = 'chip';
    const count = Object.values(mapping).filter(k => k === s.key).length;
    btn.textContent = `${{MODEL.lang === 'ar' ? (s.name_ar || s.name) : (s.name_en || s.name)}} (${{count}})`;
    btn.onclick = () => filterSubsystem(s.key, btn);
    chipsContainer.appendChild(btn);
  }});
}}

function filterSubsystem(key, btnElem) {{
  activeFilter = key;
  document.querySelectorAll('.filter-chips .chip').forEach(c => c.classList.remove('active'));
  if (btnElem) btnElem.classList.add('active');
  else if (chipsContainer.firstElementChild) chipsContainer.firstElementChild.classList.add('active');

  const mapping = (MODEL.subsystems && MODEL.subsystems.mapping) ? MODEL.subsystems.mapping : {{}};
  const {{ tablesData }} = MODEL;

  Object.keys(tablesData).forEach(tname => {{
    const card = document.getElementById(`card-${{tname}}`);
    const svgNode = document.getElementById(`svg-node-${{tname}}`);
    const match = (key === 'all') || (mapping[tname] === key);
    if (card) card.style.display = match ? 'block' : 'none';
    if (svgNode) svgNode.style.display = match ? 'block' : 'none';
  }});
}}

// Search Filter
function handleSearch(q) {{
  const query = q.toLowerCase().trim();
  const {{ tablesData }} = MODEL;
  Object.keys(tablesData).forEach(tname => {{
    const card = document.getElementById(`card-${{tname}}`);
    const svgNode = document.getElementById(`svg-node-${{tname}}`);
    const match = !query || tname.toLowerCase().includes(query) || (card && card.textContent.toLowerCase().includes(query));
    if (card) card.style.display = match ? 'block' : 'none';
    if (svgNode) svgNode.style.display = match ? 'block' : 'none';
  }});
}}

renderDiagram();
renderDictionary();
renderSubsystemChips();
</script>
</body>
</html>"""
    return html

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
    - Fully draggable and interactive SVG ER diagram with dynamic real-time relation recalculation.
    - Strict LTR text formatting ensuring column names & types stay strictly inside table boundaries in both RTL & LTR modes.
    - Theme-aware SVG styling (Dark & Light) synchronized with document theme.
    - Interactive selection, relationship tracing, and connection highlighting.
    - Toolbar controls: Zoom (+, -, 1:1), Fit to View, Orthogonal/Curved line mode, Fullscreen toggle, Auto-Layout.
    - Client-side instant search and subsystem filtering synchronized with canvas & dictionary.
    - Full Executive Data Dictionary with column details, PK/FK badges, and comments.
    - Print-ready CSS for direct browser PDF export.
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
            positions[t] = {"x": col * 340 + 60, "y": row * 280 + 60, "width": 280, "height": 180}
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

    title_text = "تقرير المخطط المعماري التفاعلي • ERD Studio Pro" if is_ar else "Interactive Architecture Report • ERD Studio Pro"

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
  --bg-table-node: #111827;
  --border: #334155;
  --border-light: #1e293b;
  --text: #f8fafc;
  --text-muted: #94a3b8;
  --accent: #38bdf8;
  --accent-glow: rgba(56, 189, 248, 0.25);
  --success: #10b981;
  --purple: #a78bfa;
  --amber: #f59e0b;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Tahoma, Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Consolas, "Courier New", monospace;
  --canvas-grid: #1e293b;
}}
[data-theme="light"] {{
  --bg: #f8fafc;
  --bg-card: #ffffff;
  --bg-card-subtle: #f1f5f9;
  --bg-table-node: #ffffff;
  --border: #cbd5e1;
  --border-light: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --accent: #0284c7;
  --accent-glow: rgba(2, 132, 199, 0.2);
  --success: #059669;
  --purple: #7c3aed;
  --amber: #d97706;
  --canvas-grid: #e2e8f0;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  overflow-x: hidden;
  transition: background-color 0.2s, color 0.2s;
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
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}
.brand {{
  display: flex;
  align-items: center;
  gap: 12px;
}}
.brand-badge {{
  background: var(--accent-glow);
  color: var(--accent);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 800;
  border: 1px solid var(--accent);
  letter-spacing: 0.5px;
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
  padding: 7px 14px;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  transition: all 0.15s ease;
  user-select: none;
}}
.btn:hover {{
  background: var(--bg-card-subtle);
  border-color: var(--accent);
  color: var(--accent);
}}
.btn.primary {{
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
}}
.btn.primary:hover {{
  filter: brightness(1.1);
  box-shadow: 0 0 12px var(--accent-glow);
}}
.btn.active {{
  background: var(--accent-glow);
  border-color: var(--accent);
  color: var(--accent);
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
  box-shadow: 0 2px 4px rgba(0,0,0,0.04);
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
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s;
}}
.canvas-card.is-fullscreen {{
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 99999 !important;
  border-radius: 0 !important;
  border: none !important;
}}
.canvas-card.is-fullscreen .canvas-viewport {{
  height: calc(100vh - 54px) !important;
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
  flex-wrap: wrap;
}}
.canvas-viewport {{
  height: 620px;
  position: relative;
  overflow: hidden;
  background-color: var(--bg);
  background-image: radial-gradient(circle, var(--canvas-grid) 1.2px, transparent 1.2px);
  background-size: 24px 24px;
  cursor: grab;
}}
.canvas-viewport.is-panning {{
  cursor: grabbing !important;
}}
.canvas-viewport.is-dragging-table {{
  cursor: grabbing !important;
}}

/* SVG Viewport & Strict LTR Text Formatting */
#viewportSvg {{
  width: 100%;
  height: 100%;
  display: block;
  direction: ltr !important;
  unicode-bidi: isolate;
  user-select: none;
}}
#viewportSvg * {{
  direction: ltr !important;
  unicode-bidi: isolate;
}}
#viewportSvg text {{
  direction: ltr !important;
  unicode-bidi: isolate;
  font-variant-numeric: tabular-nums;
  user-select: none;
}}

/* Table Node in SVG */
.table-node-svg {{
  cursor: grab;
  transition: opacity 0.2s;
}}
.table-node-svg.dragging {{
  cursor: grabbing !important;
}}
.table-node-svg:hover .table-rect-bg {{
  stroke: var(--accent);
  stroke-width: 2px;
}}
.table-node-svg.selected .table-rect-bg {{
  stroke: var(--accent) !important;
  stroke-width: 2.5px !important;
  filter: drop-shadow(0 0 10px var(--accent-glow));
}}
.table-node-svg.partner .table-rect-bg {{
  stroke: var(--purple) !important;
  stroke-width: 2px !important;
  filter: drop-shadow(0 0 6px rgba(167, 139, 250, 0.3));
}}
.table-node-svg.dimmed {{
  opacity: 0.35 !important;
}}

/* Relationship Lines */
.rel-line {{
  transition: stroke 0.2s, stroke-width 0.2s, opacity 0.2s;
  pointer-events: stroke;
  cursor: pointer;
}}
.rel-line:hover {{
  stroke: var(--accent) !important;
  stroke-width: 2.5px !important;
}}
.rel-line.highlighted {{
  stroke: var(--accent) !important;
  stroke-width: 2.5px !important;
  stroke-dasharray: none !important;
  opacity: 1 !important;
}}
.rel-line.dimmed {{
  opacity: 0.12 !important;
}}

/* Canvas Overlay Badge */
.canvas-hud {{
  position: absolute;
  bottom: 14px;
  right: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 11.5px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
  pointer-events: none;
  font-family: var(--font-mono);
  z-index: 10;
}}
[dir="rtl"] .canvas-hud {{
  right: auto;
  left: 16px;
}}

/* Filter & Search Bar */
.filter-bar {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
  flex-wrap: wrap;
}}
.search-box {{
  flex: 1;
  min-width: 260px;
  position: relative;
}}
.search-input {{
  width: 100%;
  padding: 9px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}}
.search-input:focus {{
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}}
.filter-chips {{
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}}
.chip {{
  padding: 5px 12px;
  border-radius: 7px;
  font-size: 11.5px;
  font-weight: 600;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  transition: all 0.15s ease;
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
  transition: border-color 0.2s, box-shadow 0.2s;
}}
.table-card:hover, .table-card.highlighted {{
  border-color: var(--accent);
  box-shadow: 0 0 16px var(--accent-glow);
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
  padding: 9px 14px;
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
.badge.pk {{ background: rgba(167, 139, 250, 0.18); color: var(--purple); border: 1px solid var(--purple); }}
.badge.fk {{ background: var(--accent-glow); color: var(--accent); border: 1px solid var(--accent); }}

/* Print Rules */
@media print {{
  .report-header, .canvas-toolbar, .filter-bar, .canvas-tools, .canvas-viewport, .canvas-hud {{
    display: none !important;
  }}
  body {{ background: #fff !important; color: #000 !important; }}
  .table-card {{ page-break-inside: avoid; border: 1px solid #ccc !important; margin-bottom: 16px; box-shadow: none !important; }}
  .table-head {{ background: #f0f0f0 !important; }}
  .badge.pk {{ color: #000 !important; border: 1px solid #000 !important; }}
  .badge.fk {{ color: #000 !important; border: 1px solid #000 !important; }}
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
    <button class="btn" onclick="toggleTheme()" title="{'تبديل المظهر (فاتح / داكن)' if is_ar else 'Toggle Theme (Light / Dark)'}">🌓 <span id="lblTheme">{'المظهر' if is_ar else 'Theme'}</span></button>
    <button class="btn primary" onclick="window.print()" title="{'طباعة أو تصدير PDF' if is_ar else 'Print / PDF'}">🖨 <span>{'طباعة / PDF' if is_ar else 'Print / PDF'}</span></button>
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
  <div class="canvas-card" id="canvasCard">
    <div class="canvas-toolbar">
      <div style="font-weight:700; font-size:13px; display:flex; align-items:center; gap:8px;">
        <span>🗺</span>
        <span>{'مخطط الجداول والعلاقات التفاعلي (اسحب الجداول لتحريكها بحرية)' if is_ar else 'Interactive ER Diagram (Drag tables freely)'}</span>
      </div>
      <div class="canvas-tools">
        <button class="btn" onclick="zoomIn()" title="{'تكبير' if is_ar else 'Zoom In'}">🔍+</button>
        <button class="btn" onclick="resetZoom()" title="{'ضبط 1:1' if is_ar else 'Reset 1:1'}">1:1</button>
        <button class="btn" onclick="zoomOut()" title="{'تصغير' if is_ar else 'Zoom Out'}">🔍-</button>
        <button class="btn" onclick="fitView()" title="{'ملاءمة المخطط بالكامل داخل الشاشة' if is_ar else 'Fit all tables into viewport'}">⛶ {'ملاءمة' if is_ar else 'Fit'}</button>
        <button class="btn" id="btnLineStyle" onclick="toggleLineRouting()" title="{'تبديل نمط الخطوط (منحني / متعامد)' if is_ar else 'Toggle line routing style'}">🔀 <span id="lblLineStyle">{'منحني' if is_ar else 'Curved'}</span></button>
        <button class="btn" onclick="autoLayoutTables()" title="{'إعادة ترتيب الجداول تلقائياً' if is_ar else 'Auto-arrange tables grid'}">🔄 {'ترتيب تلقائي' if is_ar else 'Auto-Layout'}</button>
        <button class="btn" id="btnFullscreen" onclick="toggleFullscreen()" title="{'ملء الشاشة' if is_ar else 'Toggle Fullscreen'}">⛶ {'ملء الشاشة' if is_ar else 'Fullscreen'}</button>
      </div>
    </div>
    <div class="canvas-viewport" id="viewport">
      <svg id="viewportSvg" direction="ltr" style="direction: ltr !important;">
        <defs>
          <marker id="relArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" id="arrowPath" />
          </marker>
        </defs>
        <g id="scene" direction="ltr" style="direction: ltr !important;">
          <g id="relationsGroup"></g>
          <g id="tablesGroup"></g>
        </g>
      </svg>
      <div class="canvas-hud" id="canvasHud">
        <span>{'تكبير:' if is_ar else 'Zoom:'} <b id="hudZoom">85%</b></span>
        <span>•</span>
        <span>{'الجداول:' if is_ar else 'Tables:'} <b id="hudTables">{len(tables_data)}</b></span>
      </div>
    </div>
  </div>

  <!-- Search & Filter Controls -->
  <div class="filter-bar">
    <div class="search-box">
      <input type="text" id="searchInput" class="search-input" placeholder="{'بحث فوري في الجداول والحقول والشروحات...' if is_ar else 'Instant search across tables and attributes...'}" oninput="handleSearch(this.value)">
    </div>
    <div class="filter-chips" id="chipsContainer">
      <button class="chip active" onclick="filterSubsystem('all', this)">{'الكل' if is_ar else 'All'} ({len(tables_data)})</button>
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

const TABLE_WIDTH = 280;
const HEADER_HEIGHT = 36;
const ROW_HEIGHT = 22;

let zoom = 0.85;
let panX = 60;
let panY = 60;
let isPanning = false;
let panStartX = 0, panStartY = 0;

// Dragging table variables
let draggedTable = null;
let isTableDragging = false;
let dragOffsetX = 0, dragOffsetY = 0;
let dragStartClientX = 0, dragStartClientY = 0;
let hasTableMoved = false;

let selectedTable = null;
let activeFilter = 'all';
let lineRoutingMode = 'bezier'; // 'bezier' or 'orthogonal'
let isFullscreen = false;

const viewport = document.getElementById('viewport');
const scene = document.getElementById('scene');
const tablesGroup = document.getElementById('tablesGroup');
const relationsGroup = document.getElementById('relationsGroup');
const dictList = document.getElementById('dictList');
const chipsContainer = document.getElementById('chipsContainer');
const canvasCard = document.getElementById('canvasCard');
const hudZoom = document.getElementById('hudZoom');
const hudTables = document.getElementById('hudTables');

function updateTransform() {{
  scene.setAttribute('transform', `translate(${{panX}}, ${{panY}}) scale(${{zoom}})`);
  if (hudZoom) hudZoom.textContent = `${{Math.round(zoom * 100)}}%`;
}}

function zoomIn() {{
  const cx = viewport.clientWidth / 2;
  const cy = viewport.clientHeight / 2;
  zoomAtPoint(cx, cy, 1.2);
}}

function zoomOut() {{
  const cx = viewport.clientWidth / 2;
  const cy = viewport.clientHeight / 2;
  zoomAtPoint(cx, cy, 0.8);
}}

function resetZoom() {{
  zoom = 1.0;
  panX = 60;
  panY = 60;
  updateTransform();
}}

function zoomAtPoint(screenX, screenY, factor) {{
  const oldZoom = zoom;
  const newZoom = Math.min(Math.max(zoom * factor, 0.15), 3.0);
  if (newZoom === oldZoom) return;

  const worldX = (screenX - panX) / oldZoom;
  const worldY = (screenY - panY) / oldZoom;

  zoom = newZoom;
  panX = screenX - worldX * zoom;
  panY = screenY - worldY * zoom;
  updateTransform();
}}

// Dynamic bounding-box Fit to View
function fitView() {{
  const visibleTables = Object.keys(MODEL.tablesData).filter(t => {{
    const node = document.getElementById(`svg-node-${{t}}`);
    return node && node.style.display !== 'none';
  }});
  if (!visibleTables.length) return;

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  visibleTables.forEach(t => {{
    const p = MODEL.positions[t] || {{ x: 60, y: 60, width: TABLE_WIDTH, height: 180 }};
    const cols = (MODEL.tablesData[t] && MODEL.tablesData[t].columns) ? MODEL.tablesData[t].columns.length : 4;
    const h = HEADER_HEIGHT + Math.min(cols, 12) * ROW_HEIGHT + 14;
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x + TABLE_WIDTH);
    maxY = Math.max(maxY, p.y + h);
  }});

  const vpW = viewport.clientWidth || 1200;
  const vpH = viewport.clientHeight || 600;
  const contentW = Math.max(maxX - minX + 140, 300);
  const contentH = Math.max(maxY - minY + 140, 300);

  const scaleX = vpW / contentW;
  const scaleY = vpH / contentH;
  zoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.2), 1.25);

  const midX = (minX + maxX) / 2;
  const midY = (minY + maxY) / 2;
  panX = vpW / 2 - midX * zoom;
  panY = vpH / 2 - midY * zoom;

  updateTransform();
}}

function toggleFullscreen() {{
  isFullscreen = !isFullscreen;
  if (isFullscreen) {{
    canvasCard.classList.add('is-fullscreen');
    document.getElementById('btnFullscreen').innerHTML = "⛶ " + (MODEL.lang === 'ar' ? 'تصغير' : 'Exit');
  }} else {{
    canvasCard.classList.remove('is-fullscreen');
    document.getElementById('btnFullscreen').innerHTML = "⛶ " + (MODEL.lang === 'ar' ? 'ملء الشاشة' : 'Fullscreen');
  }}
  setTimeout(fitView, 60);
}}

window.addEventListener('keydown', e => {{
  if (e.key === 'Escape' && isFullscreen) {{
    toggleFullscreen();
  }}
}});

function toggleLineRouting() {{
  lineRoutingMode = (lineRoutingMode === 'bezier' ? 'orthogonal' : 'bezier');
  const lbl = document.getElementById('lblLineStyle');
  if (lbl) lbl.textContent = (lineRoutingMode === 'bezier' ? (MODEL.lang === 'ar' ? 'منحني' : 'Curved') : (MODEL.lang === 'ar' ? 'متعامد' : 'Orthogonal'));
  updateRelationLines();
}}

function autoLayoutTables() {{
  const visible = Object.keys(MODEL.tablesData).filter(t => {{
    const node = document.getElementById(`svg-node-${{t}}`);
    return node && node.style.display !== 'none';
  }});
  const colsCount = Math.max(Math.ceil(Math.sqrt(visible.length * 1.5)), 3);
  visible.forEach((tname, i) => {{
    const col = i % colsCount;
    const row = Math.floor(i / colsCount);
    MODEL.positions[tname] = {{
      x: col * 330 + 80,
      y: row * 300 + 80,
      width: TABLE_WIDTH
    }};
    const node = document.getElementById(`svg-node-${{tname}}`);
    if (node) {{
      node.setAttribute('transform', `translate(${{MODEL.positions[tname].x}}, ${{MODEL.positions[tname].y}})`);
    }}
  }});
  updateRelationLines();
  fitView();
}}

// Viewport Canvas Panning
viewport.addEventListener('mousedown', e => {{
  if (e.button !== 0) return;
  if (e.target.closest('.table-node-svg')) return; // Table drag handled separately

  isPanning = true;
  panStartX = e.clientX - panX;
  panStartY = e.clientY - panY;
  viewport.classList.add('is-panning');

  // Deselect on empty canvas click
  clearSelection();
}});

window.addEventListener('mousemove', e => {{
  if (isPanning) {{
    panX = e.clientX - panStartX;
    panY = e.clientY - panStartY;
    updateTransform();
    return;
  }}

  if (isTableDragging && draggedTable) {{
    const dx = Math.abs(e.clientX - dragStartClientX);
    const dy = Math.abs(e.clientY - dragStartClientY);
    if (dx > 3 || dy > 3) hasTableMoved = true;

    const vpRect = viewport.getBoundingClientRect();
    const worldX = (e.clientX - vpRect.left - panX) / zoom;
    const worldY = (e.clientY - vpRect.top - panY) / zoom;

    const pos = MODEL.positions[draggedTable];
    pos.x = Math.round(worldX - dragOffsetX);
    pos.y = Math.round(worldY - dragOffsetY);

    const node = document.getElementById(`svg-node-${{draggedTable}}`);
    if (node) {{
      node.setAttribute('transform', `translate(${{pos.x}}, ${{pos.y}})`);
    }}

    // Real-time update connected lines
    updateRelationLines(draggedTable);
  }}
}});

window.addEventListener('mouseup', () => {{
  if (isPanning) {{
    isPanning = false;
    viewport.classList.remove('is-panning');
  }}

  if (isTableDragging && draggedTable) {{
    const node = document.getElementById(`svg-node-${{draggedTable}}`);
    if (node) node.classList.remove('dragging');
    viewport.classList.remove('is-dragging-table');

    if (!hasTableMoved) {{
      // Simple click without drag -> Select & Focus
      selectAndFocusTable(draggedTable);
    }}

    isTableDragging = false;
    draggedTable = null;
  }}
}});

// Zoom on mouse wheel centered at pointer
viewport.addEventListener('wheel', e => {{
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.12 : 0.89;
  const rect = viewport.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  zoomAtPoint(mouseX, mouseY, factor);
}}, {{ passive: false }});

function toggleTheme() {{
  const cur = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
}}

// Calculate Smart Routing Line Path
function calculateLinePath(cp, pp, mode) {{
  const cw = TABLE_WIDTH;
  const pw = TABLE_WIDTH;
  const ch = cp.height || 180;
  const ph = pp.height || 180;

  let x1, y1, x2, y2;
  if (cp.x + cw < pp.x - 20) {{
    // Child is left of Parent
    x1 = cp.x + cw;
    y1 = cp.y + 42;
    x2 = pp.x;
    y2 = pp.y + 42;
  }} else if (pp.x + pw < cp.x - 20) {{
    // Child is right of Parent
    x1 = cp.x;
    y1 = cp.y + 42;
    x2 = pp.x + pw;
    y2 = pp.y + 42;
  }} else {{
    // Vertically stacked or overlapping horizontally
    x1 = cp.x + cw / 2;
    y1 = (cp.y < pp.y) ? (cp.y + ch) : cp.y;
    x2 = pp.x + pw / 2;
    y2 = (cp.y < pp.y) ? pp.y : (pp.y + ph);
  }}

  if (mode === 'orthogonal') {{
    const midX = (x1 + x2) / 2;
    return `M ${{x1}} ${{y1}} L ${{midX}} ${{y1}} L ${{midX}} ${{y2}} L ${{x2}} ${{y2}}`;
  }} else {{
    const dx = Math.max(Math.abs(x2 - x1) * 0.45, 40);
    const c1x = x1 + (x2 >= x1 ? dx : -dx);
    const c2x = x2 - (x2 >= x1 ? dx : -dx);
    return `M ${{x1}} ${{y1}} C ${{c1x}} ${{y1}}, ${{c2x}} ${{y2}}, ${{x2}} ${{y2}}`;
  }}
}}

// Real-time Update of Relation Lines
function updateRelationLines(tableFilter) {{
  MODEL.fkList.forEach((f, idx) => {{
    if (tableFilter && f.child !== tableFilter && f.parent !== tableFilter) return;
    const cp = MODEL.positions[f.child];
    const pp = MODEL.positions[f.parent];
    if (!cp || !pp) return;
    const path = document.getElementById(`rel-path-${{idx}}`);
    if (path) {{
      path.setAttribute('d', calculateLinePath(cp, pp, lineRoutingMode));
    }}
  }});
}}

// Draw SVG Tables & Relations
function renderDiagram() {{
  tablesGroup.innerHTML = '';
  relationsGroup.innerHTML = '';

  const {{ tablesData, fkList, positions }} = MODEL;

  // Draw Foreign Key Lines
  fkList.forEach((f, idx) => {{
    const cp = positions[f.child];
    const pp = positions[f.parent];
    if (!cp || !pp) return;

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('id', `rel-path-${{idx}}`);
    path.setAttribute('d', calculateLinePath(cp, pp, lineRoutingMode));
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#64748b');
    path.setAttribute('stroke-width', '1.8');
    path.setAttribute('stroke-dasharray', '4 3');
    path.setAttribute('class', `rel-line rel-${{f.child}} rel-${{f.parent}}`);
    path.setAttribute('marker-end', 'url(#relArrow)');

    const titleEl = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    titleEl.textContent = `${{f.child}} -> ${{f.parent}} (${{f.cols || ''}})`;
    path.appendChild(titleEl);

    relationsGroup.appendChild(path);
  }});

  // Draw Interactive Tables
  Object.keys(tablesData).forEach(tname => {{
    const data = tablesData[tname];
    const pos = positions[tname] || {{ x: 80, y: 80 }};
    const cols = data.columns || [];
    const pks = data.pks || [];

    const visibleCols = cols.slice(0, 11);
    const extraCols = cols.length - visibleCols.length;
    const cardHeight = HEADER_HEIGHT + visibleCols.length * ROW_HEIGHT + (extraCols > 0 ? 28 : 10);
    pos.width = TABLE_WIDTH;
    pos.height = cardHeight;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'table-node-svg');
    g.setAttribute('id', `svg-node-${{tname}}`);
    g.setAttribute('direction', 'ltr');
    g.setAttribute('transform', `translate(${{pos.x}}, ${{pos.y}})`);
    g.style.direction = 'ltr';

    // Mousedown for Table Dragging
    g.addEventListener('mousedown', e => {{
      if (e.button !== 0) return;
      e.stopPropagation();

      draggedTable = tname;
      isTableDragging = true;
      hasTableMoved = false;
      dragStartClientX = e.clientX;
      dragStartClientY = e.clientY;

      const vpRect = viewport.getBoundingClientRect();
      const worldX = (e.clientX - vpRect.left - panX) / zoom;
      const worldY = (e.clientY - vpRect.top - panY) / zoom;
      dragOffsetX = worldX - pos.x;
      dragOffsetY = worldY - pos.y;

      g.classList.add('dragging');
      viewport.classList.add('is-dragging-table');

      // Bring table to front in SVG
      tablesGroup.appendChild(g);
    }});

    // Table Card Body Rect
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('class', 'table-rect-bg');
    rect.setAttribute('width', TABLE_WIDTH);
    rect.setAttribute('height', cardHeight);
    rect.setAttribute('rx', '9');
    rect.setAttribute('fill', 'var(--bg-table-node)');
    rect.setAttribute('stroke', 'var(--border)');
    rect.setAttribute('stroke-width', '1.5');
    rect.setAttribute('id', `rect-${{tname}}`);
    g.appendChild(rect);

    // Table Header Rect
    const titleRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    titleRect.setAttribute('width', TABLE_WIDTH);
    titleRect.setAttribute('height', HEADER_HEIGHT);
    titleRect.setAttribute('rx', '9');
    titleRect.setAttribute('fill', 'var(--bg-card-subtle)');
    titleRect.setAttribute('stroke', 'var(--border)');
    titleRect.setAttribute('stroke-width', '1');
    g.appendChild(titleRect);

    // Cover bottom corners of header rect
    const headerPatch = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    headerPatch.setAttribute('x', '0');
    headerPatch.setAttribute('y', HEADER_HEIGHT - 6);
    headerPatch.setAttribute('width', TABLE_WIDTH);
    headerPatch.setAttribute('height', '6');
    headerPatch.setAttribute('fill', 'var(--bg-card-subtle)');
    g.appendChild(headerPatch);

    // Table Header Title Text (Centered, strict LTR)
    const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    txt.setAttribute('x', TABLE_WIDTH / 2);
    txt.setAttribute('y', 23);
    txt.setAttribute('text-anchor', 'middle');
    txt.setAttribute('direction', 'ltr');
    txt.setAttribute('fill', 'var(--accent)');
    txt.setAttribute('font-family', 'var(--font-mono)');
    txt.setAttribute('font-size', '12');
    txt.setAttribute('font-weight', '700');
    txt.style.direction = 'ltr';
    txt.textContent = tname.length > 25 ? tname.slice(0, 24) + '…' : tname;
    const titleTip = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    titleTip.textContent = tname;
    txt.appendChild(titleTip);
    g.appendChild(txt);

    // Columns sample (Strict LTR text-anchor to avoid RTL flip)
    visibleCols.forEach((col, ci) => {{
      const cy = HEADER_HEIGHT + 17 + ci * ROW_HEIGHT;
      const isPk = pks.includes(col.name);
      const isFk = fkList.some(f => f.child === tname && (f.cols || '').toLowerCase() === col.name.toLowerCase());

      // Column Name (Anchored strictly to left at x=16)
      const colTxt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      colTxt.setAttribute('x', '16');
      colTxt.setAttribute('y', cy);
      colTxt.setAttribute('text-anchor', 'start');
      colTxt.setAttribute('direction', 'ltr');
      colTxt.setAttribute('fill', isPk ? 'var(--purple)' : 'var(--text)');
      colTxt.setAttribute('font-size', '11');
      colTxt.setAttribute('font-family', 'var(--font-mono)');
      if (isPk) colTxt.setAttribute('font-weight', '700');
      colTxt.style.direction = 'ltr';
      colTxt.style.unicodeBidi = 'isolate';

      const prefix = isPk ? '🔑 ' : (isFk ? '🔗 ' : '');
      const rawName = col.name;
      const displayName = rawName.length > 17 ? rawName.slice(0, 16) + '…' : rawName;
      colTxt.textContent = prefix + displayName;

      const colTip = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      colTip.textContent = `${{rawName}} (${{col.type || 'UNKNOWN'}})`;
      colTxt.appendChild(colTip);
      g.appendChild(colTxt);

      // Data Type (Anchored strictly to right at x=264)
      const typeTxt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      typeTxt.setAttribute('x', '264');
      typeTxt.setAttribute('y', cy);
      typeTxt.setAttribute('text-anchor', 'end');
      typeTxt.setAttribute('direction', 'ltr');
      typeTxt.setAttribute('fill', 'var(--text-muted)');
      typeTxt.setAttribute('font-size', '10');
      typeTxt.setAttribute('font-family', 'var(--font-mono)');
      typeTxt.style.direction = 'ltr';
      typeTxt.style.unicodeBidi = 'isolate';

      const rawType = col.type || '';
      const displayType = rawType.length > 13 ? rawType.slice(0, 12) + '…' : rawType;
      typeTxt.textContent = displayType;
      g.appendChild(typeTxt);
    }});

    // Extra columns indicator if more than 11 columns
    if (extraCols > 0) {{
      const moreTxt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      moreTxt.setAttribute('x', TABLE_WIDTH / 2);
      moreTxt.setAttribute('y', cardHeight - 8);
      moreTxt.setAttribute('text-anchor', 'middle');
      moreTxt.setAttribute('direction', 'ltr');
      moreTxt.setAttribute('fill', 'var(--text-muted)');
      moreTxt.setAttribute('font-size', '10.5');
      moreTxt.setAttribute('font-style', 'italic');
      moreTxt.style.direction = 'ltr';
      moreTxt.textContent = (MODEL.lang === 'ar') ? `+ ${{extraCols}} حقول أخرى...` : `+ ${{extraCols}} more columns...`;
      g.appendChild(moreTxt);
    }}

    tablesGroup.appendChild(g);
  }});
}}

// Select & Focus Table with visual relationship isolation
function selectAndFocusTable(tname) {{
  selectedTable = tname;

  // Highlight in SVG
  document.querySelectorAll('.table-node-svg').forEach(n => {{
    n.classList.remove('selected', 'partner', 'dimmed');
  }});
  document.querySelectorAll('.rel-line').forEach(l => {{
    l.classList.remove('highlighted', 'dimmed');
  }});

  const selectedNode = document.getElementById(`svg-node-${{tname}}`);
  if (selectedNode) selectedNode.classList.add('selected');

  // Identify connected relations and partner tables
  const connectedPartners = new Set();
  MODEL.fkList.forEach((f, idx) => {{
    const line = document.getElementById(`rel-path-${{idx}}`);
    if (!line) return;
    if (f.child === tname || f.parent === tname) {{
      line.classList.add('highlighted');
      connectedPartners.add(f.child === tname ? f.parent : f.child);
    }} else {{
      line.classList.add('dimmed');
    }}
  }});

  // Highlight partners and dim unrelated tables
  Object.keys(MODEL.tablesData).forEach(t => {{
    if (t === tname) return;
    const node = document.getElementById(`svg-node-${{t}}`);
    if (!node) return;
    if (connectedPartners.has(t)) {{
      node.classList.add('partner');
    }} else {{
      node.classList.add('dimmed');
    }}
  }});

  // Scroll to Data Dictionary Card
  document.querySelectorAll('.table-card').forEach(c => c.classList.remove('highlighted'));
  const card = document.getElementById(`card-${{tname}}`);
  if (card) {{
    card.classList.add('highlighted');
    card.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
  }}
}}

function clearSelection() {{
  selectedTable = null;
  document.querySelectorAll('.table-node-svg').forEach(n => {{
    n.classList.remove('selected', 'partner', 'dimmed');
  }});
  document.querySelectorAll('.rel-line').forEach(l => {{
    l.classList.remove('highlighted', 'dimmed');
  }});
  document.querySelectorAll('.table-card').forEach(c => c.classList.remove('highlighted'));
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
        <button class="btn" onclick="focusAndPanToTable('${{tname}}')">🎯 {'عرض في المخطط' if is_ar else 'View in Diagram'}</button>
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

// Center canvas on table
function focusAndPanToTable(tname) {{
  selectAndFocusTable(tname);
  const pos = MODEL.positions[tname];
  if (!pos) return;

  const vpW = viewport.clientWidth;
  const vpH = viewport.clientHeight;
  panX = vpW / 2 - (pos.x + TABLE_WIDTH / 2) * zoom;
  panY = vpH / 2 - (pos.y + (pos.height || 180) / 2) * zoom;
  updateTransform();

  // Smooth scroll canvas into view
  canvasCard.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
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

  let visibleCount = 0;
  Object.keys(tablesData).forEach(tname => {{
    const card = document.getElementById(`card-${{tname}}`);
    const svgNode = document.getElementById(`svg-node-${{tname}}`);
    const match = (key === 'all') || (mapping[tname] === key);
    if (card) card.style.display = match ? 'block' : 'none';
    if (svgNode) svgNode.style.display = match ? 'block' : 'none';
    if (match) visibleCount++;
  }});

  // Update relations visibility
  MODEL.fkList.forEach((f, idx) => {{
    const line = document.getElementById(`rel-path-${{idx}}`);
    if (!line) return;
    const cMatch = (key === 'all') || (mapping[f.child] === key);
    const pMatch = (key === 'all') || (mapping[f.parent] === key);
    line.style.display = (cMatch && pMatch) ? 'block' : 'none';
  }});

  if (hudTables) hudTables.textContent = visibleCount;
  fitView();
}}

// Search Filter
function handleSearch(q) {{
  const query = q.toLowerCase().trim();
  const {{ tablesData }} = MODEL;
  let visibleCount = 0;

  Object.keys(tablesData).forEach(tname => {{
    const card = document.getElementById(`card-${{tname}}`);
    const svgNode = document.getElementById(`svg-node-${{tname}}`);
    const match = !query || tname.toLowerCase().includes(query) || (card && card.textContent.toLowerCase().includes(query));
    if (card) card.style.display = match ? 'block' : 'none';
    if (svgNode) svgNode.style.display = match ? 'block' : 'none';
    if (match) visibleCount++;
  }});

  // Update relations visibility
  MODEL.fkList.forEach((f, idx) => {{
    const line = document.getElementById(`rel-path-${{idx}}`);
    if (!line) return;
    const cMatch = !query || f.child.toLowerCase().includes(query);
    const pMatch = !query || f.parent.toLowerCase().includes(query);
    line.style.display = (cMatch && pMatch) ? 'block' : 'none';
  }});

  if (hudTables) hudTables.textContent = visibleCount;
}}

// Initialize
renderDiagram();
renderDictionary();
renderSubsystemChips();
fitView();
</script>
</body>
</html>"""
    return html

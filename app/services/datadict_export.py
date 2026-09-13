"""Generate a Data Dictionary .xlsx workbook from a parsed schema model (tablesData/fkList).

Produces one sheet per table in the classic ERD Data Dictionary layout matching
the structure read by datadict_import (so the output can be re-imported).
"""
import io
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

_HEADER_EN = [
    "#", "Field name", "Caption / prompt", "Data type", "Length / Size",
    "PK", "M", "U", "I", "FK", "References", "check",
    "Field Status", "Default Value", "Description",
]
_HEADER_AR = [
    "م", "إسم الحقل", "الإسم المستعار", "نوع البيانات", "الطول",
    "م أساسي", "إجباري", "فريد", "فهرس", "م ثانوي", "مرجع الجدول",
    "القيد", "نوع الحقل في الواجهة", "القيمة الإفتراضية", "ملاحظات",
]

_HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
_HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
_AR_FILL = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
_AR_FONT = Font(name="Calibri", bold=True, color="1F3864", size=10)
_TITLE_FONT = Font(name="Calibri", bold=True, color="1F3864", size=12)
_TYPE_FONT = Font(name="Consolas", size=10, color="404040")
_NAME_FONT = Font(name="Calibri", size=10, color="202020")
_PK_FONT = Font(name="Consolas", bold=True, size=9, color="7C3AED")
_THIN = Side(style="thin", color="B0B0B0")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)

_TYPE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.+)\))?\s*$")


def _split_type(raw):
    m = _TYPE_RE.match(str(raw).strip())
    if not m:
        return str(raw).strip(), ""
    return m.group(1), (m.group(2) or "")


def build_workbook_bytes(tables_data: dict, fk_list: list) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # Build a fast FK lookup: (child_table, child_col) → {parent, parent_col}
    fk_map = {}
    for f in fk_list:
        parent = f.get("parent", "")
        for col in (f.get("cols") or "").split(","):
            col = col.strip()
            if col:
                fk_map[(f.get("child", ""), col)] = parent

    for tname in sorted(tables_data.keys()):
        data = tables_data[tname]
        pks = set(data.get("pks") or [])
        columns = data.get("columns") or []

        ws = wb.create_sheet(title=tname[:31])

        # Row 0: Table title
        t_comment = data.get("comment") or data.get("description")
        ws["A1"] = f"{tname} - {t_comment}" if t_comment else f"{tname}"
        ws["A1"].font = _TITLE_FONT
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=15)

        # Row 1: English headers
        for ci, hdr in enumerate(_HEADER_EN, start=1):
            c = ws.cell(row=2, column=ci, value=hdr)
            c.font = _HEADER_FONT
            c.fill = _HEADER_FILL
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = _BORDER

        # Row 2: Arabic headers
        for ci, hdr in enumerate(_HEADER_AR, start=1):
            c = ws.cell(row=3, column=ci, value=hdr)
            c.font = _AR_FONT
            c.fill = _AR_FILL
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = _BORDER

        # Data rows
        for ri, col in enumerate(columns, start=1):
            cname = col.get("name", "")
            base, params = _split_type(col.get("type", ""))
            parent = fk_map.get((tname, cname), "")
            caption = col.get("caption") if (col.get("caption") and col.get("caption") != "-") else (col.get("comment") or "-")
            description = col.get("description") if (col.get("description") and col.get("description") != "-") else (col.get("comment") or "-")
            unique_mark = "✓" if col.get("unique") else ""
            default_val = col.get("default_value") or "-"

            row_vals = [
                ri,                                         # #
                cname,                                      # Field name
                caption,                                    # Caption / prompt
                base,                                       # Data type
                params if params else "-",                  # Length
                "✓" if cname in pks else "",                # PK
                "✓" if not col.get("nullable", True) else "",  # M
                unique_mark,                                # U
                "",                                         # I (not tracked)
                "✓" if parent else "",                      # FK
                f"{parent}({cname})" if parent else "-",   # References
                col.get("check") or "-",                    # check
                "Hidden" if cname in pks else "Text",       # Field Status
                default_val,                                # Default
                description,                                # Description
            ]
            row_num = ri + 3  # header rows 2+3 (1-indexed)
            for ci, val in enumerate(row_vals, start=1):
                c = ws.cell(row=row_num, column=ci, value=val)
                c.border = _BORDER
                if ci == 1:
                    c.alignment = Alignment(horizontal="center")
                elif ci == 5:
                    c.font = _TYPE_FONT
                    c.alignment = Alignment(horizontal="left", readingOrder=1)
                elif ci == 6:
                    c.font = _PK_FONT
                    c.alignment = Alignment(horizontal="center")
                elif ci in (2, 4, 10):
                    c.alignment = Alignment(horizontal="left", readingOrder=1)
                else:
                    c.alignment = Alignment(horizontal="center")

        # Column widths
        widths = [5, 24, 18, 16, 12, 8, 8, 8, 8, 8, 32, 8, 16, 12, 28]
        for ci, w in enumerate(widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = w

    # Write to buffer
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()
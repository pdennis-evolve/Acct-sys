import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def render_invoice_pdf(invoice, company_settings) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = []

    company_name = company_settings.company_name if company_settings else "Your Company"
    elements.append(Paragraph(company_name, styles["Title"]))
    if company_settings:
        addr_bits = [
            company_settings.address_line1,
            company_settings.address_line2,
            ", ".join(filter(None, [company_settings.city, company_settings.state, company_settings.postal_code])),
        ]
        for bit in filter(None, addr_bits):
            elements.append(Paragraph(bit, styles["Normal"]))
    elements.append(Spacer(1, 0.25 * inch))

    elements.append(Paragraph(f"Invoice {invoice.invoice_number}", styles["Heading2"]))
    elements.append(Paragraph(f"Status: {invoice.status.upper()}", styles["Normal"]))
    elements.append(Paragraph(f"Issue Date: {invoice.issue_date.isoformat()}", styles["Normal"]))
    elements.append(Paragraph(f"Due Date: {invoice.due_date.isoformat()}", styles["Normal"]))
    elements.append(Spacer(1, 0.15 * inch))

    if invoice.customer:
        c = invoice.customer
        elements.append(Paragraph("Bill To:", styles["Heading4"]))
        elements.append(Paragraph(c.company_name or c.display_name, styles["Normal"]))
        if c.billing_address_line1:
            elements.append(Paragraph(c.billing_address_line1, styles["Normal"]))
        city_line = ", ".join(filter(None, [c.billing_city, c.billing_state, c.billing_postal_code]))
        if city_line:
            elements.append(Paragraph(city_line, styles["Normal"]))
    elements.append(Spacer(1, 0.25 * inch))

    data = [["Description", "Qty", "Unit Price", "Amount"]]
    for line in invoice.lines:
        data.append([line.description, str(line.quantity), f"${line.unit_price}", f"${line.amount}"])
    table = Table(data, colWidths=[3.2 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d2d2d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))

    totals_data = [
        ["Subtotal", f"${invoice.subtotal}"],
        ["Tax", f"${invoice.tax_total}"],
        ["Total", f"${invoice.total}"],
        ["Balance Due", f"${invoice.balance_due}"],
    ]
    totals_table = Table(totals_data, colWidths=[5.2 * inch, 1.2 * inch])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
    ]))
    elements.append(totals_table)

    if invoice.memo:
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("Memo", styles["Heading4"]))
        elements.append(Paragraph(invoice.memo, styles["Normal"]))

    doc.build(elements)
    return buf.getvalue()

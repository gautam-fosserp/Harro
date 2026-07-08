# Copyright (c) 2026, Fosserp and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.report.stock_ledger.stock_ledger import execute as stock_ledger_execute
from frappe.utils import get_datetime, format_datetime, fmt_money


def execute(filters=None):
    show_outward = filters.get("show_outward", False) if filters else False
    if show_outward:
        columns = get_outward_columns()
    else:
        columns = get_columns()
    data = get_data(filters)

    # For outward view in the report grid, transform raw data into
    # the 11-column layout matching the Excel / Expected sheet.
    if show_outward and data:
        data = transform_outward_rows_for_view(data)

    return columns, data


@frappe.whitelist()
def get_export_report_from_delivery_note(delivery_note):
    """Generate export report from Delivery Note"""
    try:
        # Get Delivery Note details
        dn = frappe.get_doc("Delivery Note", delivery_note)
        
        # Get company details
        company = frappe.get_doc("Company", dn.company) if dn.company else None
        
        # Prepare data for export report
        export_data = []
        
        # Process each item in Delivery Note
        for item in dn.items:
            # Get batches used for this item
            batches_data = get_batches_from_delivery_note_item(dn.name, item.name, item.item_code, item.qty)
            
            # For each batch, get raw material details from source document
            # Create one row per raw material (not aggregated)
            all_raw_materials = []
            for batch_row in batches_data:
                # Get source document details (Purchase Receipt or Stock Entry)
                raw_material_data = get_raw_material_from_batch(
                    batch_row.get('batch_no'),
                    batch_row.get('qty'),
                    item.item_code,
                    item.item_name,
                    item.description,
                    item.uom,
                    dn.posting_date,
                    dn.posting_time,
                    dn.name
                )
                
                if raw_material_data:
                    all_raw_materials.extend(raw_material_data)
            
            # Create one row per raw material
            # First row shows finished product details, subsequent rows have blank finished product columns
            if all_raw_materials:
                for idx, rm_row in enumerate(all_raw_materials):
                    # Format raw material values
                    rm_row['wh_assessable_value'] = fmt_money(rm_row.get('wh_assessable_value', 0) or 0, currency="INR") if rm_row.get('wh_assessable_value', 0) else 'Nil'
                    rm_row['wh_duty_bcd'] = fmt_money(rm_row.get('wh_duty_bcd', 0) or 0, currency="INR") if rm_row.get('wh_duty_bcd', 0) else 'Nil'
                    rm_row['wh_duty_igst'] = fmt_money(rm_row.get('wh_duty_igst', 0) or 0, currency="INR") if rm_row.get('wh_duty_igst', 0) else 'Nil'
                    rm_row['wh_duty_comp_cess'] = fmt_money(rm_row.get('wh_duty_comp_cess', 0) or 0, currency="INR") if rm_row.get('wh_duty_comp_cess', 0) else 'Nil'
                    
                    # Mark if this is not the first row for this finished product (to blank out finished product details)
                    rm_row['is_subsequent_row'] = (idx > 0)
                    
                    export_data.append(rm_row)
        
        # If no data found, create a row with Delivery Note details and Nil for raw materials
        if not export_data:
            # Get shipping bill and invoice details from Delivery Note
            shipping_bill = getattr(dn, 'custom_shipping_bill_no', None) or ""
            shipping_bill_date = getattr(dn, 'custom_shipping_bill_date', None)
            if shipping_bill_date:
                shipping_bill_date = frappe.format(shipping_bill_date, {"fieldtype": "Date"})
            shipping_bill_display = f"{shipping_bill} / {shipping_bill_date}" if shipping_bill else ""
            
            gst_invoice = dn.name
            gst_invoice_date = frappe.format(dn.posting_date, {"fieldtype": "Date"})
            gst_invoice_display = f"{gst_invoice} / {gst_invoice_date}"
            
            removal_date = format_receipt_datetime(dn.posting_date, dn.posting_time)
            
            # Create export row for each item
            for item in dn.items:
                export_data.append({
                    "removal_date": removal_date,
                    "shipping_bill": shipping_bill_display or gst_invoice_display,
                    "gst_invoice": gst_invoice_display,
                    "description": item.description or item.item_name or item.item_code,
                    "quantity": format_quantity_with_uqc(item.qty, item.uom),
                    "assessable_value": fmt_money(item.base_net_amount or 0, currency="INR"),
                    "export_duty": "Nil",
                    "tax_igst": "Nil",
                    "tax_comp_cess": "Nil",
                    "wh_description": "Nil",
                    "wh_quantity": "Nil",
                    "wh_assessable_value": "Nil",
                    "wh_duty_bcd": "Nil",
                    "wh_duty_igst": "Nil",
                    "wh_duty_comp_cess": "Nil"
                })
        
        # Generate HTML using outward template
        return generate_export_report_html(export_data, company, dn.posting_date, dn.posting_date)
        
    except Exception as e:
        frappe.log_error(f"Error generating export report from Delivery Note {delivery_note}: {str(e)}")
        frappe.throw(f"Failed to generate export report: {str(e)}")


@frappe.whitelist()
def get_print_format_html(filters=None):
    """Return HTML for print format"""
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    data = get_data(filters)
    
    # Get company details
    company = None
    if filters.get("company"):
        try:
            company = frappe.get_doc("Company", filters.get("company"))
        except Exception:
            pass
    
    # Determine if this is outward report
    show_outward = filters.get("show_outward", False)
    
    # Get the appropriate HTML template
    import os
    if show_outward:
        template_path = os.path.join(
            os.path.dirname(__file__),
            "import_receipt_outward.html"
        )
    else:
        template_path = os.path.join(
            os.path.dirname(__file__),
            "import_receipt.html"
        )
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Prepare template variables
    unit_name = getattr(company, 'name', None) if company else None
    if not unit_name:
        unit_name = "M/s Harro Hoefliger Packaging Systems Pvt. Ltd"
    
    unit_address = getattr(company, 'custom_unit_address', None) if company else None
    if not unit_address:
        unit_address = "Shed No. - 62, DITPL, SW - 51, Apparel Park, Phase 2, KIADB Industrial Area, Doddaballapur, Bengaluru Rural, Karnataka - 561203"
    
    iec = getattr(company, 'custom_iec', None) if company else None
    if not iec:
        iec = "0313016071"
    
    gstin = company.gstin if company and company.gstin else "29AADCH1078B1ZU"
    commissionerate = getattr(company, 'custom_commissionerate', None) if company else None
    if not commissionerate:
        commissionerate = "Nil"
    
    from_date = frappe.format(filters.get("from_date"), {"fieldtype": "Date"}) if filters.get("from_date") else ""
    to_date = frappe.format(filters.get("to_date"), {"fieldtype": "Date"}) if filters.get("to_date") else ""
    
    # Determine report title based on filter
    report_title = "REMOVALS (OUTWARD)" if show_outward else "RECEIPTS (IMPORTS)"
    
    # Generate table rows based on report type
    if show_outward:
        # Transform outward data into the 11-column combined layout
        data = transform_outward_rows_for_view(data) if data else []
        table_rows = generate_outward_table_rows(data)
    else:
        table_rows = generate_inward_table_rows(data)
    
    # Replace template variables
    html = template.replace("{{ unit_name }}", escape_html(unit_name))
    html = html.replace("{{ unit_address }}", escape_html(unit_address))
    html = html.replace("{{ iec }}", escape_html(iec))
    html = html.replace("{{ gstin }}", escape_html(gstin))
    html = html.replace("{{ commissionerate }}", escape_html(commissionerate))
    html = html.replace("{{ from_date }}", escape_html(from_date))
    html = html.replace("{{ to_date }}", escape_html(to_date))
    if not show_outward:
        # Only replace report_title for inward template
        html = html.replace("{{ report_title }}", escape_html(report_title))
    html = html.replace("{{ table_rows }}", table_rows)
    
    # Ensure UTF-8 encoding is properly set
    # The HTML template already has charset declaration, but ensure it's at the beginning
    if not html.strip().startswith('<!DOCTYPE'):
        # If no DOCTYPE, ensure charset is at the very beginning
        if '<meta charset' not in html[:500]:
            html = '<meta charset="UTF-8">\n' + html
    
    return html.encode('utf-8').decode('utf-8')


@frappe.whitelist()
def export_outward_to_excel(filters=None):
    """Export outward report data to Excel format"""
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    # Ensure show_outward is True
    filters['show_outward'] = True
    
    # Get raw outward data
    data = get_data(filters)
    
    # Prepare Excel data – reuse the same 11-column transformation as the report grid
    from frappe.utils.xlsxutils import make_xlsx
    
    # Headers for outward report (single header row, matching provided sheet)
    headers = [
        "Date of issue",
        "Description of goods",
        "Quantity with UQC",
        "Value",
        "Date and time of removal",
        "Description of goods",
        "Quantity with UQC",
        "Value",
        "Delivery Challan No.",
        "Details of Job worker",
        "GSTIN (if applicable)",
    ]
    
    # Prepare rows
    rows = [headers]
    
    view_rows = transform_outward_rows_for_view(data) if data else []
    for view_row in view_rows:
        rows.append([
            view_row.get("goods_date_of_issue", ""),
            view_row.get("goods_description", ""),
            view_row.get("goods_quantity_with_uqc", ""),
            view_row.get("goods_value", ""),
            view_row.get("job_removal_datetime", ""),
            view_row.get("job_description", ""),
            view_row.get("job_quantity_with_uqc", ""),
            view_row.get("job_value", ""),
            view_row.get("delivery_challan_no", ""),
            view_row.get("job_worker_details", ""),
            view_row.get("job_worker_gstin", ""),
        ])
    
    # Create Excel file
    xlsx_file = make_xlsx(rows, "Outward Removals Report")
    
    # Return file for download
    from frappe.desk.utils import provide_binary_file
    provide_binary_file("Outward_Removals_Report", "xlsx", xlsx_file.getvalue())


def get_job_worker_details(stock_entry_name):
    """Return (delivery_challan_no, job_worker_details, job_worker_gstin) for a Send to Subcontractor Stock Entry.

    GSTIN is resolved from:
      1. Supplier master (gstin field), else
      2. Primary Address linked to Supplier (Address.gstin)
    """
    delivery_challan_no = ""
    job_worker_details = ""
    job_worker_gstin = ""

    if not stock_entry_name:
        return delivery_challan_no, job_worker_details, job_worker_gstin

    try:
        se = frappe.get_doc("Stock Entry", stock_entry_name)
    except frappe.DoesNotExistError:
        return delivery_challan_no, job_worker_details, job_worker_gstin

    # Delivery Challan No: custom field or fallback to Stock Entry name
    delivery_challan_no = se.get("delivery_challan_no") or se.name

    subcontracting_order = se.get("subcontracting_order")
    if subcontracting_order:
        try:
            so = frappe.get_doc("Subcontracting Order", subcontracting_order)
            supplier = so.supplier
            supplier_name = getattr(so, "supplier_name", "") or supplier or ""
            job_worker_details = supplier_name

            # Try to get GSTIN from Supplier master
            if supplier:
                job_worker_gstin = frappe.db.get_value("Supplier", supplier, "gstin") or ""

                # If not found on Supplier, try primary Address linked to Supplier
                if not job_worker_gstin:
                    supplier_address = frappe.db.get_value(
                        "Dynamic Link",
                        {
                            "link_doctype": "Supplier",
                            "link_name": supplier,
                            "parenttype": "Address",
                        },
                        "parent",
                    )
                    if supplier_address:
                        job_worker_gstin = frappe.db.get_value("Address", supplier_address, "gstin") or ""
        except frappe.DoesNotExistError:
            pass

    return delivery_challan_no, job_worker_details, job_worker_gstin


def transform_outward_rows_for_view(raw_rows):
    """
    Take the raw outward rows from get_data and build two independent
    lists (goods-issued and job-work), then combine them row-wise so
    that the left and right sections are logically separate, like the
    Expected Excel.
    """
    if not raw_rows:
        return []

    goods_rows = []
    job_rows = []

    for raw in raw_rows:
        row = frappe._dict(raw)

        # Core outward values
        removal_date_raw = str(row.get("removal_date", row.get("receipt_date_time", "")) or "")
        description_raw = str(row.get("description", row.get("description_of_goods", "")) or "")
        quantity_raw = str(row.get("quantity", row.get("quantity_with_uqc", "")) or "")
        assessable_value_raw = str(row.get("assessable_value", "") or "")

        stock_entry_name = row.get("stock_entry")
        is_jobwork = False

        if stock_entry_name:
            se_type = frappe.db.get_value("Stock Entry", stock_entry_name, "stock_entry_type")
            if se_type == "Send to Subcontractor":
                is_jobwork = True

        if is_jobwork:
            # Build job-work side only
            delivery_challan_no, job_worker_details, job_worker_gstin = get_job_worker_details(
                stock_entry_name
            )
            job_rows.append(
                frappe._dict(
                    {
                        "job_removal_datetime": removal_date_raw,
                        "job_description": description_raw,
                        "job_quantity_with_uqc": quantity_raw,
                        "job_value": assessable_value_raw,
                        "delivery_challan_no": delivery_challan_no,
                        "job_worker_details": job_worker_details,
                        "job_worker_gstin": job_worker_gstin,
                    }
                )
            )
        else:
            # Build goods-issued side only
            goods_rows.append(
                frappe._dict(
                    {
                        "goods_date_of_issue": removal_date_raw,
                        "goods_description": description_raw,
                        "goods_quantity_with_uqc": quantity_raw,
                        "goods_value": assessable_value_raw,
                    }
                )
            )

    # Combine both lists row-wise (like two independent tables side-by-side)
    combined = []
    max_len = max(len(goods_rows), len(job_rows))

    for idx in range(max_len):
        combined_row = frappe._dict()
        if idx < len(goods_rows):
            combined_row.update(goods_rows[idx])
        if idx < len(job_rows):
            combined_row.update(job_rows[idx])
        combined.append(combined_row)

    return combined


def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    import html
    return html.escape(str(text))


def clean_description(text):
    """Strip HTML markup from a rich-text description, keeping line breaks
    between block-level elements (e.g. Item description stored as <p>/<div> HTML)."""
    if not text:
        return ""
    text = str(text)
    if "<" not in text:
        return escape_html(text)

    import re
    text = re.sub(r"(?i)<\s*(br|/p|/div|/li)\s*/?>", "\n", text)
    text = re.sub(r"(?i)<[^>]+>", "", text)

    import html
    text = html.unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return escape_html(text).replace("\n", "<br>")


def generate_inward_table_rows(data):
    """Generate table rows for inward/receipts report"""
    table_rows = ""
    if data:
        # First pass: count how many rows belong to each Purchase Receipt.
        # This is required to generate a single <td> for Assessable Value
        # with the correct rowspan, so it visually merges across item rows.
        pr_row_counts = {}
        for row in data:
            pr_name = row.get("purchase_receipt")
            if pr_name:
                pr_row_counts[pr_name] = pr_row_counts.get(pr_name, 0) + 1

        # Track for which Purchase Receipt we've already rendered the
        # Assessable Value <td> (with rowspan). Subsequent rows for the
        # same PR will not render that cell at all, so the rowspan cell
        # from the first row visually covers them.
        rendered_assessable_for_pr = set()

        for row in data:
            bill_entry = escape_html(str(row.get('bill_of_entry_no_and_date', '') or ''))
            customs_station = escape_html(str(row.get('customs_station', '') or ''))
            bond_details = escape_html(str(row.get('bond_details', '') or ''))
            insurance_details = escape_html(str(row.get('insurance_details', '') or ''))
            description = clean_description(row.get('description_of_goods', ''))
            invoice = escape_html(str(row.get('invoice_no_and_date', '') or ''))
            quantity = escape_html(str(row.get('quantity_with_uqc', '') or ''))
            # Build Assessable Value cell with rowspan per Purchase Receipt
            assessable_cell_html = ""
            pr_name = row.get('purchase_receipt')
            raw_assessable_value = row.get('assessable_value')

            if raw_assessable_value:
                if pr_name and pr_name in pr_row_counts:
                    # Only render the cell once per Purchase Receipt, with rowspan
                    if pr_name not in rendered_assessable_for_pr:
                        rowspan = pr_row_counts.get(pr_name, 1)
                        assessable_display = escape_html(
                            fmt_money(raw_assessable_value or 0, currency="INR")
                        )
                        assessable_cell_html = (
                            f'<td style="border: 1px solid #000; padding: 6px; '
                            f'text-align: right;" rowspan="{rowspan}">{assessable_display}</td>'
                        )
                        rendered_assessable_for_pr.add(pr_name)
                    else:
                        # Subsequent rows for this PR rely on the rowspan cell,
                        # so we do not render any <td> for this column here.
                        assessable_cell_html = ""
                else:
                    # For non-Purchase-Receipt rows (e.g. Stock Entry), show normally
                    assessable_display = escape_html(
                        fmt_money(raw_assessable_value or 0, currency="INR")
                    )
                    assessable_cell_html = (
                        f'<td style="border: 1px solid #000; padding: 6px; '
                        f'text-align: right;">{assessable_display}</td>'
                    )

            # Format remaining duty values and escape HTML
            duty_bcd = escape_html(fmt_money(row.get('duty_bcd', 0) or 0, currency="INR")) if row.get('duty_bcd') else ''
            duty_igst = escape_html(fmt_money(row.get('duty_igst', 0) or 0, currency="INR")) if row.get('duty_igst') else ''
            duty_comp_cess = escape_html(fmt_money(row.get('duty_comp_cess', 0) or 0, currency="INR")) if row.get('duty_comp_cess') else ''
            transport = escape_html(str(row.get('registration_no_transport', '') or ''))
            lock_no = escape_html(str(row.get('lock_no', '') or ''))
            receipt_dt = escape_html(str(row.get('receipt_date_time', '') or ''))
            
            table_rows += f"""
            <tr>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{bill_entry}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{customs_station}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left; font-size: 10px;">{bond_details}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{insurance_details}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{description}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{invoice}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{quantity}</td>
                {assessable_cell_html}
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{duty_bcd}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{duty_igst}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{duty_comp_cess}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{transport}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{lock_no}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{receipt_dt}</td>
            </tr>
            """
    else:
        table_rows = '<tr><td colspan="15" style="border: 1px solid #000; padding: 8px; text-align: center;">N/A</td></tr>'
    
    return table_rows


def generate_outward_table_rows(data):
    """Generate table rows for outward/export report"""
    table_rows = ""
    if data:
        for row in data:
            row = frappe._dict(row)

            goods_date = str(row.get("goods_date_of_issue", "") or "")
            goods_desc = str(row.get("goods_description", "") or "")
            goods_qty = str(row.get("goods_quantity_with_uqc", "") or "")
            goods_val = str(row.get("goods_value", "") or "")

            job_date = str(row.get("job_removal_datetime", "") or "")
            job_desc = str(row.get("job_description", "") or "")
            job_qty = str(row.get("job_quantity_with_uqc", "") or "")
            job_val = str(row.get("job_value", "") or "")

            delivery_challan_no = str(row.get("delivery_challan_no", "") or "")
            job_worker_details = str(row.get("job_worker_details", "") or "")
            job_worker_gstin = str(row.get("job_worker_gstin", "") or "")

            table_rows += f"""
            <tr>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{escape_html(goods_date)}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{clean_description(goods_desc)}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{escape_html(goods_qty)}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{escape_html(goods_val)}</td>

                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{escape_html(job_date)}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{clean_description(job_desc)}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{escape_html(job_qty)}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{escape_html(job_val)}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{escape_html(delivery_challan_no)}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{escape_html(job_worker_details)}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{escape_html(job_worker_gstin)}</td>
            </tr>
            """
    else:
        table_rows = '<tr><td colspan="11" style="border: 1px solid #000; padding: 8px; text-align: center;">N/A</td></tr>'
    
    return table_rows


def get_batches_from_delivery_note_item(delivery_note, item_row_name, item_code, qty):
    """Get batches used in Delivery Note item"""
    # Check if item has serial and batch bundle
    item_row = frappe.db.get_value("Delivery Note Item", item_row_name, ["serial_and_batch_bundle"], as_dict=1)
    
    if not item_row or not item_row.serial_and_batch_bundle:
        return []
    
    # Get batch details from serial and batch bundle
    batch_data = frappe.db.sql("""
        SELECT
            sbe.batch_no,
            sbe.qty
        FROM `tabSerial and Batch Entry` as sbe
        WHERE sbe.parent = %s
            AND sbe.batch_no IS NOT NULL
    """, (item_row.serial_and_batch_bundle,), as_dict=1)
    
    return batch_data


def get_raw_material_from_batch(batch_no, batch_qty, finished_item_code, finished_item_name, finished_description, finished_uom, posting_date, posting_time, delivery_note):
    """Get raw material import details from batch rm_batch_details table"""
    if not batch_no:
        return []
    
    result = []
    
    # Get RM Batch details from the finished product batch
    rm_batch_details = frappe.db.get_all(
        "RM Batch details",
        filters={"parent": batch_no, "parenttype": "Batch", "parentfield": "rm_batch_details"},
        fields=["batch_no", "invoice_no", "bill_of_entry"]
    )
    
    if not rm_batch_details:
        return []
    
    # Format removal date from Delivery Note
    removal_date = format_receipt_datetime(posting_date, posting_time)
    
    # Get shipping bill from Delivery Note
    dn = frappe.get_doc("Delivery Note", delivery_note)
    shipping_bill = getattr(dn, 'custom_shipping_bill_no', None) or ""
    shipping_bill_date = getattr(dn, 'custom_shipping_bill_date', None)
    if shipping_bill_date:
        shipping_bill_date = frappe.format(shipping_bill_date, {"fieldtype": "Date"})
    shipping_bill_display = f"{shipping_bill} / {shipping_bill_date}" if shipping_bill else ""
    
    # GST Invoice from Delivery Note
    gst_invoice = delivery_note
    gst_invoice_date = frappe.format(posting_date, {"fieldtype": "Date"})
    gst_invoice_display = f"{gst_invoice} / {gst_invoice_date}"
    
    # For each raw material batch, get import details from its source document
    for rm_batch_row in rm_batch_details:
        rm_batch_no = rm_batch_row.get('batch_no')
        if not rm_batch_no:
            continue
        
        # Get raw material batch source document
        rm_batch = frappe.db.get_value("Batch", rm_batch_no, ["reference_doctype", "reference_name", "item"], as_dict=1)
        
        if not rm_batch or not rm_batch.reference_doctype or not rm_batch.reference_name:
            continue
        
        # Get import details from source document
        if rm_batch.reference_doctype == "Purchase Receipt":
            pr_data = frappe.db.sql("""
                SELECT
                    pr.assessable_value_inr,
                    pr.basic_custom_duty_inr,
                    pr.tax_amount_inr,
                    pr.compensation_cess_inr,
                    pr_item.item_code,
                    pr_item.item_name,
                    pr_item.description,
                    pr_item.uom,
                    pr_item.qty
                FROM `tabPurchase Receipt` as pr
                INNER JOIN `tabPurchase Receipt Item` as pr_item ON pr.name = pr_item.parent
                WHERE pr.name = %s AND pr_item.item_code = %s
                LIMIT 1
            """, (rm_batch.reference_name, rm_batch.item), as_dict=1)
            
            if pr_data:
                row = pr_data[0]
                result.append({
                    "removal_date": removal_date,
                    "shipping_bill": shipping_bill_display or gst_invoice_display,
                    "gst_invoice": gst_invoice_display,
                    "description": finished_description or finished_item_name or finished_item_code,
                    "quantity": format_quantity_with_uqc(batch_qty, finished_uom),
                    "assessable_value": fmt_money(row.assessable_value_inr or 0, currency="INR"),
                    "export_duty": "Nil",
                    "tax_igst": "Nil",
                    "tax_comp_cess": "Nil",
                    "wh_description": row.description or row.item_name or row.item_code or "Nil",
                    "wh_quantity": format_quantity_with_uqc(row.qty, row.uom),
                    "wh_assessable_value": row.assessable_value_inr or 0,  # Store raw value for aggregation
                    "wh_duty_bcd": row.basic_custom_duty_inr or 0,  # Store raw value for aggregation
                    "wh_duty_igst": row.tax_amount_inr or 0,  # Store raw value for aggregation
                    "wh_duty_comp_cess": row.compensation_cess_inr or 0  # Store raw value for aggregation
                })
    
        elif rm_batch.reference_doctype == "Stock Entry":
            se_data = frappe.db.sql("""
                SELECT
                    se.assessable_value_inr,
                    se.basic_custom_duty_inr,
                    se.tax_amount_inr,
                    se.compensation_cess_inr,
                    se_item.item_code,
                    se_item.item_name,
                    se_item.description,
                    se_item.uom,
                    se_item.qty
                FROM `tabStock Entry` as se
                INNER JOIN `tabStock Entry Detail` as se_item ON se.name = se_item.parent
                WHERE se.name = %s AND se_item.item_code = %s
                LIMIT 1
            """, (rm_batch.reference_name, rm_batch.item), as_dict=1)
            
            if se_data:
                row = se_data[0]
                result.append({
                    "removal_date": removal_date,
                    "shipping_bill": shipping_bill_display or gst_invoice_display,
                    "gst_invoice": gst_invoice_display,
                    "description": finished_description or finished_item_name or finished_item_code,
                    "quantity": format_quantity_with_uqc(batch_qty, finished_uom),
                    "assessable_value": fmt_money(row.assessable_value_inr or 0, currency="INR"),
                    "export_duty": "Nil",
                    "tax_igst": "Nil",
                    "tax_comp_cess": "Nil",
                    "wh_description": row.description or row.item_name or row.item_code or "Nil",
                    "wh_quantity": format_quantity_with_uqc(row.qty, row.uom),
                    "wh_assessable_value": row.assessable_value_inr or 0,  # Store raw value for aggregation
                    "wh_duty_bcd": row.basic_custom_duty_inr or 0,  # Store raw value for aggregation
                    "wh_duty_igst": row.tax_amount_inr or 0,  # Store raw value for aggregation
                    "wh_duty_comp_cess": row.compensation_cess_inr or 0  # Store raw value for aggregation
                })
    
    return result


def get_import_details_from_batch_source(batch_no, item_code):
    """Get import details from batch source document (Purchase Receipt or Stock Entry)"""
    if not batch_no:
        return {}
    
    # Get batch details
    batch = frappe.db.get_value("Batch", batch_no, ["reference_doctype", "reference_name"], as_dict=1)
    
    if not batch or not batch.reference_doctype or not batch.reference_name:
        return {}
    
    if batch.reference_doctype == "Purchase Receipt":
        pr_data = frappe.db.sql("""
            SELECT
                pr.assessable_value_inr,
                pr.basic_custom_duty_inr,
                pr.tax_amount_inr,
                pr.compensation_cess_inr
            FROM `tabPurchase Receipt` as pr
            INNER JOIN `tabPurchase Receipt Item` as pr_item ON pr.name = pr_item.parent
            WHERE pr.name = %s AND pr_item.item_code = %s
            LIMIT 1
        """, (batch.reference_name, item_code), as_dict=1)
        
        if pr_data:
            row = pr_data[0]
            return {
                "assessable_value": row.assessable_value_inr or 0,
                "duty_bcd": row.basic_custom_duty_inr or 0,
                "duty_igst": row.tax_amount_inr or 0,
                "duty_comp_cess": row.compensation_cess_inr or 0
            }
    
    elif batch.reference_doctype == "Stock Entry":
        se_data = frappe.db.sql("""
            SELECT
                se.assessable_value_inr,
                se.basic_custom_duty_inr,
                se.tax_amount_inr,
                se.compensation_cess_inr
            FROM `tabStock Entry` as se
            INNER JOIN `tabStock Entry Detail` as se_item ON se.name = se_item.parent
            WHERE se.name = %s AND se_item.item_code = %s
            LIMIT 1
        """, (batch.reference_name, item_code), as_dict=1)
        
        if se_data:
            row = se_data[0]
            return {
                "assessable_value": row.assessable_value_inr or 0,
                "duty_bcd": row.basic_custom_duty_inr or 0,
                "duty_igst": row.tax_amount_inr or 0,
                "duty_comp_cess": row.compensation_cess_inr or 0
            }
    
    return {}


def generate_export_report_html(export_data, company, from_date, to_date):
    """Generate HTML for export report"""
    # Get the outward HTML template
    import os
    template_path = os.path.join(
        os.path.dirname(__file__),
        "import_receipt_outward.html"
    )
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Prepare template variables
    unit_name = getattr(company, 'custom_unit_name', None) if company else None
    if not unit_name:
        unit_name = "M/s Harro Hoefliger Packaging Systems Pvt. Ltd"
    
    unit_address = getattr(company, 'custom_unit_address', None) if company else None
    if not unit_address:
        unit_address = "Shed No. - 62, DITPL, SW - 51, Apparel Park, Phase 2, KIADB Industrial Area, Doddaballapur, Bengaluru Rural, Karnataka - 561203"
    
    iec = getattr(company, 'custom_iec', None) if company else None
    if not iec:
        iec = "0313016071"
    
    gstin = company.gstin if company and company.gstin else "29AADCH1078B1ZU"
    commissionerate = getattr(company, 'custom_commissionerate', None) if company else None
    if not commissionerate:
        commissionerate = "Nil"
    
    from_date_str = frappe.format(from_date, {"fieldtype": "Date"}) if from_date else ""
    to_date_str = frappe.format(to_date, {"fieldtype": "Date"}) if to_date else ""
    
    # Generate table rows
    table_rows = ""
    if export_data:
        for row in export_data:
            # Check if this is a subsequent row (should blank out finished product details)
            is_subsequent = row.get('is_subsequent_row', False)
            
            # Finished product details (blank if subsequent row)
            removal_date = '' if is_subsequent else escape_html(str(row.get('removal_date', '') or ''))
            shipping_bill = '' if is_subsequent else escape_html(str(row.get('shipping_bill', '') or ''))
            gst_invoice = '' if is_subsequent else escape_html(str(row.get('gst_invoice', '') or ''))
            description = '' if is_subsequent else clean_description(row.get('description', ''))
            quantity = '' if is_subsequent else escape_html(str(row.get('quantity', '') or ''))
            assessable_value = '' if is_subsequent else escape_html(str(row.get('assessable_value', '') or ''))
            export_duty = '' if is_subsequent else escape_html(str(row.get('export_duty', 'Nil') or 'Nil'))
            tax_igst = '' if is_subsequent else escape_html(str(row.get('tax_igst', 'Nil') or 'Nil'))
            tax_comp_cess = '' if is_subsequent else escape_html(str(row.get('tax_comp_cess', 'Nil') or 'Nil'))
            
            # Raw material details (always shown)
            wh_description = escape_html(str(row.get('wh_description', 'Nil') or 'Nil'))
            wh_quantity = escape_html(str(row.get('wh_quantity', 'Nil') or 'Nil'))
            wh_assessable_value = escape_html(str(row.get('wh_assessable_value', 'Nil') or 'Nil'))
            wh_duty_bcd = escape_html(str(row.get('wh_duty_bcd', 'Nil') or 'Nil'))
            wh_duty_igst = escape_html(str(row.get('wh_duty_igst', 'Nil') or 'Nil'))
            wh_duty_comp_cess = escape_html(str(row.get('wh_duty_comp_cess', 'Nil') or 'Nil'))
            
            table_rows += f"""
            <tr>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{removal_date}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{shipping_bill}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{gst_invoice}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{description}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{quantity}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{assessable_value}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: center;">{export_duty}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: center;">{tax_igst}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: center;">{tax_comp_cess}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: left;">{wh_description}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{wh_quantity}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{wh_assessable_value}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{wh_duty_bcd}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{wh_duty_igst}</td>
                <td style="border: 1px solid #000; padding: 6px; text-align: right;">{wh_duty_comp_cess}</td>
            </tr>
            """
    else:
        table_rows = '<tr><td colspan="15" style="border: 1px solid #000; padding: 8px; text-align: center;">N/A</td></tr>'
    
    # Replace template variables
    html = template.replace("{{ unit_name }}", escape_html(unit_name))
    html = html.replace("{{ unit_address }}", escape_html(unit_address))
    html = html.replace("{{ iec }}", escape_html(iec))
    html = html.replace("{{ gstin }}", escape_html(gstin))
    html = html.replace("{{ commissionerate }}", escape_html(commissionerate))
    html = html.replace("{{ from_date }}", escape_html(from_date_str))
    html = html.replace("{{ to_date }}", escape_html(to_date_str))
    html = html.replace("{{ table_rows }}", table_rows)
    
    # Ensure UTF-8 encoding is properly set
    if not html.strip().startswith('<!DOCTYPE'):
        if '<meta charset' not in html[:500]:
            html = '<meta charset="UTF-8">\n' + html
    
    return html.encode('utf-8').decode('utf-8')


def get_data(filters):
    if not filters or not filters.get("from_date") or not filters.get("to_date"):
        return []

    try:
        # Prepare warehouse filter - can be single warehouse or list
        warehouse_filter = filters.get("warehouse")
        if warehouse_filter:
            # If it's a string, convert to list
            if isinstance(warehouse_filter, str):
                warehouse_filter = [warehouse_filter]
            elif not isinstance(warehouse_filter, list):
                warehouse_filter = [warehouse_filter]
        
        filters_ = frappe._dict({
            "from_date": filters.get("from_date"),
            "to_date": filters.get("to_date"),
            "company": filters.get("company")
        })
        
        # Only add warehouse filter if specified
        if warehouse_filter:
            filters_["warehouse"] = warehouse_filter

        stock_ledger_data = stock_ledger_execute(filters_)[1]
        final_data = []
        
        # Track processed vouchers to avoid duplicates
        # NOTE: We only use this de-duplication for outward (removal) entries.
        # For inward (imports) we must keep one row per Stock Ledger Entry item,
        # so we do NOT skip potential duplicates there.
        processed_vouchers = set()

        # Check if outward goods filter is enabled
        show_outward = filters.get("show_outward", False)

        for row in stock_ledger_data:
            try:
                row = frappe._dict(row)
                
                if show_outward:
                    # Create a unique key for this outward transaction
                    voucher_key = f"{row.voucher_type}_{row.voucher_no}_{row.item_code}"
                    
                    # Skip if already processed for outward to avoid duplicates
                    if voucher_key in processed_vouchers:
                        continue

                    # Process outward quantities (removals from warehouse)
                    # Condition: out_qty < 1 (includes negative values and 0)
                    qty = row.out_qty
                    if not qty or qty >= 1:
                        continue
                        
                    # For outward, we want the absolute value (positive) for display
                    display_qty = abs(qty)
                    
                else:
                    # Process incoming quantities (imports)
                    qty = row.in_qty
                    # Skip if no in_qty or in_qty <= 0 (not an inward movement)
                    # Also skip if there's an outward qty (out_qty < 1)
                    if not qty or qty <= 0 or (row.out_qty and row.out_qty < 1):
                        continue
                    
                    display_qty = qty
                
                if show_outward:
                    # For outward, handle Delivery Notes
                    if row.voucher_type == "Delivery Note":
                        dn_data = get_delivery_note_outward_data(
                            row.voucher_no, display_qty, row.get('item_code'), row.get('warehouse')
                        )
                        if dn_data:
                            for dn_row in dn_data:
                                dn_row["outward_reference_doctype"] = row.voucher_type
                                dn_row["outward_reference_no"] = row.voucher_no
                            final_data.extend(dn_data)
                            processed_vouchers.add(voucher_key)
                    elif row.voucher_type == "Stock Entry":
                        se_data = get_stock_entry_data(row, display_qty, show_outward)
                        if se_data:
                            for se_row in se_data:
                                se_row["outward_reference_doctype"] = row.voucher_type
                                se_row["outward_reference_no"] = row.voucher_no
                            final_data.extend(se_data)
                            processed_vouchers.add(voucher_key)
                else:
                    # For inward, handle Purchase Receipts and Stock Entries
                    if row.voucher_type == "Purchase Receipt":
                        pr_data = get_purchase_receipt_data(row.voucher_no, display_qty, row.get('item_code'), show_outward)
                        if pr_data:
                            final_data.extend(pr_data)
                            processed_vouchers.add(voucher_key)
                    
                    elif row.voucher_type == "Stock Entry":
                        se_data = get_stock_entry_data(row, display_qty, show_outward)
                        if se_data:
                            # Only add first item from se_data to avoid duplicates
                            # (get_stock_entry_data should already return deduplicated data)
                            final_data.extend(se_data)
                            processed_vouchers.add(voucher_key)
                        
            except Exception as e:
                frappe.log_error(f"Error processing row {row.get('voucher_no', 'unknown')}: {str(e)}")
                continue
        
        return final_data
    except Exception as e:
        frappe.log_error(f"Error in import_receipt report: {str(e)}")
        return []


def get_delivery_note_outward_data(voucher_no, qty, item_code=None, warehouse=None):
    """Get outward/removal data from Delivery Note"""
    try:
        dn = frappe.get_doc("Delivery Note", voucher_no)
        result = []

        # Get shipping bill from Delivery Note
        shipping_bill = getattr(dn, 'shipping_bill_number', None) or ""
        shipping_bill_date = getattr(dn, 'shipping_bill_date', None)
        if shipping_bill_date:
            shipping_bill_date = frappe.format(shipping_bill_date, {"fieldtype": "Date"})
        shipping_bill_display = f"{shipping_bill} / {shipping_bill_date}" if shipping_bill else ""

        # GST Invoice from Delivery Note
        gst_invoice = voucher_no
        gst_invoice_date = frappe.format(dn.posting_date, {"fieldtype": "Date"})
        gst_invoice_display = f"{gst_invoice} / {gst_invoice_date}"

        # Format removal date
        removal_date = format_receipt_datetime(dn.posting_date, dn.posting_time)

        # Process each item in Delivery Note
        for item in dn.items:
            if item_code and item.item_code != item_code:
                continue
            if warehouse and item.warehouse != warehouse:
                continue

            # Get batches used for this item
            batches_data = get_batches_from_delivery_note_item(dn.name, item.name, item.item_code, item.qty)
            
            # For each batch, get raw material details from source document
            all_raw_materials = []
            for batch_row in batches_data:
                raw_material_data = get_raw_material_from_batch(
                    batch_row.get('batch_no'),
                    batch_row.get('qty'),
                    item.item_code,
                    item.item_name,
                    item.description,
                    item.uom,
                    dn.posting_date,
                    dn.posting_time,
                    dn.name
                )
                
                if raw_material_data:
                    all_raw_materials.extend(raw_material_data)
            
            # Create one row per raw material
            if all_raw_materials:
                for idx, rm_row in enumerate(all_raw_materials):
                    # Mark if this is not the first row for this finished product
                    rm_row['is_subsequent_row'] = (idx > 0)
                    result.append(rm_row)
            else:
                # If no raw material data, create a row with Delivery Note details
                result.append({
                    "removal_date": removal_date,
                    "shipping_bill": shipping_bill_display or gst_invoice_display,
                    "gst_invoice": gst_invoice_display,
                    "description": item.description or item.item_name or item.item_code,
                    "quantity": format_quantity_with_uqc(qty, item.uom),
                    "assessable_value": fmt_money(item.base_net_amount or 0, currency="INR"),
                    "export_duty": "Nil",
                    "tax_igst": "Nil",
                    "tax_comp_cess": "Nil",
                    "wh_description": "Nil",
                    "wh_quantity": "Nil",
                    "wh_assessable_value": "Nil",
                    "wh_duty_bcd": "Nil",
                    "wh_duty_igst": "Nil",
                    "wh_duty_comp_cess": "Nil"
                })
        
        return result
    except Exception as e:
        frappe.log_error(f"Error getting Delivery Note outward data: {str(e)}")
        return []


def get_purchase_receipt_data(voucher_no, qty, item_code=None, is_outward=False):
    """Get Purchase Receipt data with item details - quantity comes from stock ledger"""
    # Filter by item_code if provided to match stock ledger entry
    item_filter = ""
    params = [voucher_no]
    if item_code:
        item_filter = "AND pr_item.item_code = %s"
        params.append(item_code)
    
    pr_data = frappe.db.sql(f"""
        SELECT
            pr.name as purchase_receipt,
            pr.bill_of_entry,
            pr.bill_of_entry_date,
            pr.port_code as customs_station,
            pr.bond_doc_type,
            pr.bond_posting_date,
            pr.bond_value_inr,
            pr.bond_valid_till,
            pr.insurance_no,
            pr.insurance_date,
            pr.supplier_invoice_no,
            pr.supplier_invoice_date,
            pr.assessable_value_inr,
            pr.basic_custom_duty_inr,
            pr.tax_amount_inr,
            pr.compensation_cess_inr,
            pr.transport_registration_no,
            pr.vehicle_no,
            pr.lock_no,
            pr.posting_date,
            pr.posting_time,
            pr_item.item_code,
            pr_item.item_name,
            pr_item.description,
            pr_item.uom
            # Removed pr_item.qty from SELECT - we'll use the passed qty parameter
        FROM `tabPurchase Receipt` as pr
        INNER JOIN `tabPurchase Receipt Item` as pr_item ON pr.name = pr_item.parent
        WHERE pr.name = %s {item_filter}
    """, tuple(params), as_dict=1)

    result = []
    # Only process first matching row to avoid duplicates
    # Since we filter by item_code, there should be only one match per stock ledger entry
    if pr_data:
        row = pr_data[0]  # Take only the first matching row to ensure one row per stock ledger entry
        
        # Format Bill of Entry No. and date
        bill_of_entry_display = format_bill_of_entry(row.bill_of_entry, row.bill_of_entry_date)
        
        # Details of Bond should come directly from bond_doc_type field
        bond_details = row.bond_doc_type or ""
        
        # Format Insurance details
        insurance_details = format_insurance_details(row.insurance_no, row.insurance_date)
        
        # Format Invoice No. and date
        invoice_display = format_invoice(row.supplier_invoice_no, row.supplier_invoice_date)
        
        # Format Quantity with UQC - ALWAYS use the passed qty from stock ledger
        qty_display = format_quantity_with_uqc(qty, row.uom)
        
        # Format Date and time of receipt
        receipt_datetime = format_receipt_datetime(row.posting_date, row.posting_time)
        
        result.append({
            "bill_of_entry_no_and_date": bill_of_entry_display,
            "customs_station": row.customs_station or "",
            "bond_details": bond_details,
            "insurance_details": insurance_details,
            "description_of_goods": row.description or row.item_name or row.item_code or "",
            "invoice_no_and_date": invoice_display,
            "quantity_with_uqc": qty_display,  # Using stock ledger qty
            "assessable_value": row.assessable_value_inr or 0,
            "duty_bcd": row.basic_custom_duty_inr or 0,
            "duty_igst": row.tax_amount_inr or 0,
            "duty_comp_cess": row.compensation_cess_inr or 0,
            "registration_no_transport": (getattr(row, "transport_registration_no", None) or row.vehicle_no or ""),
            "lock_no": row.lock_no or "",
            "receipt_date_time": receipt_datetime,
            "purchase_receipt": row.purchase_receipt,
            "item_code": row.item_code
        })
    
    return result


def get_stock_entry_data(stock_ledger_row, qty, is_outward=False):
    """Get Stock Entry data with item details"""
    voucher_no = stock_ledger_row.get('voucher_no')
    item_code = stock_ledger_row.get('item_code')

    if is_outward:
        # The actual outward/removal date must come from this Stock Entry
        # (the voucher that performed the removal, matching the Stock
        # Ledger row the date filter is applied against), not from
        # whichever source document the batch traces back to.
        outward_removal_date = format_receipt_datetime(
            stock_ledger_row.get("posting_date"), stock_ledger_row.get("posting_time")
        )

        # For outward entries, we need to find the source document that created the batch
        # Check if this stock entry has batch/serial references
        if stock_ledger_row.serial_and_batch_bundle:
            # Get the source document details from batch references
            return get_batch_reference_data(
                stock_ledger_row.serial_and_batch_bundle, qty, is_outward, outward_removal_date
            )
        else:
            # If no batch bundle, try to get from the stock entry details
            se_data = get_material_receipt_data(voucher_no, qty, item_code, is_outward)
            for se_row in se_data:
                se_row["removal_date"] = outward_removal_date
            return se_data
    
    # For inward entries, check if it's Material Receipt
    stock_entry_type = frappe.get_value("Stock Entry", voucher_no, "stock_entry_type")
    
    if stock_entry_type == "Material Receipt":
        # For Material Receipt, get data directly from Stock Entry
        return get_material_receipt_data(voucher_no, qty, item_code, is_outward)

    # For other Stock Entry types, check if it has batch/serial references
    elif stock_ledger_row.serial_and_batch_bundle:
        return get_batch_reference_data(stock_ledger_row.serial_and_batch_bundle, qty, is_outward)
    
    return []


def get_material_receipt_data(voucher_no, qty, item_code=None, is_outward=False):
    """Get Material Receipt (Stock Entry) data - quantity comes from stock ledger"""
    # Filter by item_code if provided to match stock ledger entry
    item_filter = ""
    params = [voucher_no]
    if item_code:
        item_filter = "AND se_item.item_code = %s"
        params.append(item_code)
    
    # Check if bill_of_entry exists in child table (Stock Entry Detail)
    child_table_columns = frappe.db.get_table_columns("Stock Entry Detail")
    has_bill_of_entry_in_child = "bill_of_entry" in child_table_columns
    
    # Build COALESCE for bill_of_entry if it exists in child table
    # Handle empty strings by using NULLIF, then fall back to parent
    bill_of_entry_select = (
        "COALESCE(NULLIF(se_item.bill_of_entry, ''), se.bill_of_entry) as bill_of_entry"
        if has_bill_of_entry_in_child
        else "se.bill_of_entry"
    )
    
    se_data = frappe.db.sql(f"""
        SELECT
            se.name as stock_entry,
            {bill_of_entry_select},
            COALESCE(se_item.bill_of_entry_date, se.bill_of_entry_date) as bill_of_entry_date,
            se.port_code as customs_station,
            se.bond_doc_type,
            se.bond_posting_date,
            se.bond_value_inr,
            se.bond_valid_till,
            se.insurance_no,
            se.insurance_date,
            COALESCE(NULLIF(se_item.supplier_invoice_no, ''), se.supplier_invoice_no) as supplier_invoice_no,
            COALESCE(se_item.supplier_invoice_date, se.supplier_invoice_date) as supplier_invoice_date,
            COALESCE(NULLIF(se_item.supplier, ''), se.supplier) as supplier,
            se.assessable_value_inr,
            se.basic_custom_duty_inr,
            se.tax_amount_inr,
            se.compensation_cess_inr,
            se.transport_registration_no,
            se.vehicle_no,
            se.lock_no,
            se.posting_date,
            se.posting_time,
            se_item.item_code,
            se_item.item_name,
            se_item.description,
            se_item.uom
            # Removed se_item.qty from SELECT - we'll use the passed qty parameter
        FROM `tabStock Entry` as se
        INNER JOIN `tabStock Entry Detail` as se_item ON se.name = se_item.parent
        WHERE se.name = %s {item_filter}
    """, tuple(params), as_dict=1)

    result = []
    # Only process first matching row to avoid duplicates
    # Since we filter by item_code, there should be only one match per stock ledger entry
    if se_data:
        row = se_data[0]  # Take only the first matching row to ensure one row per stock ledger entry
        # For outward entries, we want to show the source document details
        if is_outward:
            # For outward, import receipt fields should come from source document
            # But the quantity should ALWAYS come from stock ledger (qty parameter)
            bill_of_entry_display = format_bill_of_entry(row.bill_of_entry, row.bill_of_entry_date) if row.bill_of_entry else "N/A"
            # Details of Bond should come directly from bond_doc_type field
            bond_details = row.bond_doc_type or ""
            insurance_details = format_insurance_details(row.insurance_no, row.insurance_date) if any([row.insurance_no, row.insurance_date]) else "N/A"
            invoice_display = format_invoice(row.supplier_invoice_no, row.supplier_invoice_date) if any([row.supplier_invoice_no, row.supplier_invoice_date]) else "N/A"
        else:
            bill_of_entry_display = format_bill_of_entry(row.bill_of_entry, row.bill_of_entry_date)
            # Details of Bond should come directly from bond_doc_type field
            bond_details = row.bond_doc_type or ""
            insurance_details = format_insurance_details(row.insurance_no, row.insurance_date)
            invoice_display = format_invoice(row.supplier_invoice_no, row.supplier_invoice_date)
        
        # Format Quantity with UQC - ALWAYS use the passed qty from stock ledger
        qty_display = format_quantity_with_uqc(qty, row.uom)
        receipt_datetime = format_receipt_datetime(row.posting_date, row.posting_time)
        
        result.append({
            "bill_of_entry_no_and_date": bill_of_entry_display,
            "customs_station": row.customs_station or "",
            "bond_details": bond_details,
            "insurance_details": insurance_details,
            "description_of_goods": row.description or row.item_name or row.item_code or "",
            "invoice_no_and_date": invoice_display,
            "quantity_with_uqc": qty_display,  # Using stock ledger qty
            "assessable_value": row.assessable_value_inr or 0 if not is_outward else 0,
            "duty_bcd": row.basic_custom_duty_inr or 0 if not is_outward else 0,
            "duty_igst": row.tax_amount_inr or 0 if not is_outward else 0,
            "duty_comp_cess": row.compensation_cess_inr or 0 if not is_outward else 0,
            "registration_no_transport": (getattr(row, "transport_registration_no", None) or row.vehicle_no or ""),
            "lock_no": row.lock_no or "",
            "receipt_date_time": receipt_datetime,
            "purchase_receipt": "",  # Stock Entry doesn't have Purchase Receipt
            "stock_entry": row.stock_entry,
            "item_code": row.item_code
        })
    
    return result


def get_batch_reference_data(serial_and_batch_bundle, qty, is_outward=False, outward_removal_date=None):
    """Get data from batch references - trace back to source document, quantity from stock ledger"""
    serial_and_batch_details = frappe.db.sql("""
        SELECT
            b.reference_doctype,
            b.reference_name,
            sbe.batch_no,
            sbe.qty
        FROM `tabSerial and Batch Entry` as sbe
        LEFT JOIN `tabBatch` as b ON b.name = sbe.batch_no
        WHERE sbe.batch_no IS NOT NULL
            AND sbe.parent = %s
    """, (serial_and_batch_bundle,), as_dict=1)

    source_doc_list = []
    seen_docs = set()

    for row in serial_and_batch_details:
        if row.reference_name and row.reference_name not in seen_docs:
            seen_docs.add(row.reference_name)
            source_doc_list.append(row)

    result = []
    for row in source_doc_list:
        doctype = row.reference_doctype
        docname = row.reference_name
        # Use the passed qty from stock ledger, not the batch qty
        display_qty = qty

        if doctype == "Purchase Receipt":
            # Get import receipt details from the source PR, but use stock ledger qty
            pr_data = get_purchase_receipt_data(docname, display_qty, None, is_outward)
            if pr_data:
                if is_outward and outward_removal_date:
                    for pr_row in pr_data:
                        pr_row["removal_date"] = outward_removal_date
                result.extend(pr_data)
        elif doctype == "Stock Entry":
            # Get import receipt details from the source Stock Entry, but use stock ledger qty
            se_data = get_material_receipt_data(docname, display_qty, None, is_outward)
            if se_data:
                if is_outward and outward_removal_date:
                    for se_row in se_data:
                        se_row["removal_date"] = outward_removal_date
                result.extend(se_data)
        else:
            # For other doctypes, try to get the source document details
            if is_outward:
                # Try to get the original import document details
                source_data = get_source_document_details(doctype, docname, display_qty, is_outward)
                if source_data:
                    if outward_removal_date:
                        for src_row in source_data:
                            src_row["removal_date"] = outward_removal_date
                    result.extend(source_data)
            else:
                # For inward, continue with generic fetch (existing code)
                # ... (keep your existing generic fetch code here)
                pass

    return result

def get_source_document_details(doctype, docname, qty, is_outward=False):
    """Get source document details for outward transactions - quantity from stock ledger"""
    if not is_outward:
        return []
    
    result = []
    
    # Try to find the original import document through batch
    if doctype == "Batch":
        # If it's a batch, try to find the source document that created this batch
        source_doc = frappe.db.get_value("Batch", docname, ["reference_doctype", "reference_name"], as_dict=1)
        if source_doc and source_doc.reference_doctype and source_doc.reference_name:
            if source_doc.reference_doctype == "Purchase Receipt":
                return get_purchase_receipt_data(source_doc.reference_name, qty, None, is_outward)
            elif source_doc.reference_doctype == "Stock Entry":
                # Check if the source Stock Entry is a Material Receipt
                stock_entry_type = frappe.get_value("Stock Entry", source_doc.reference_name, "stock_entry_type")
                if stock_entry_type == "Material Receipt":
                    return get_material_receipt_data(source_doc.reference_name, qty, None, is_outward)
    
    # For other doctypes, try to get the document directly
    try:
        if frappe.db.exists(doctype, docname):
            doc = frappe.get_doc(doctype, docname)
            
            # Check if this document has import receipt fields
            row_data = frappe._dict({
                "bill_of_entry": getattr(doc, "bill_of_entry", None),
                "bill_of_entry_date": getattr(doc, "bill_of_entry_date", None),
                "customs_station": getattr(doc, "port_code", None),
                "bond_doc_type": getattr(doc, "bond_doc_type", None),
                "bond_posting_date": getattr(doc, "bond_posting_date", None),
                "bond_value_inr": getattr(doc, "bond_value_inr", None),
                "bond_valid_till": getattr(doc, "bond_valid_till", None),
                "insurance_no": getattr(doc, "insurance_no", None),
                "insurance_date": getattr(doc, "insurance_date", None),
                "supplier_invoice_no": getattr(doc, "supplier_invoice_no", None),
                "supplier_invoice_date": getattr(doc, "supplier_invoice_date", None),
                "assessable_value_inr": getattr(doc, "assessable_value_inr", None),
                "basic_custom_duty_inr": getattr(doc, "basic_custom_duty_inr", None),
                "tax_amount_inr": getattr(doc, "tax_amount_inr", None),
                "compensation_cess_inr": getattr(doc, "compensation_cess_inr", None),
                "transport_registration_no": getattr(doc, "transport_registration_no", None),
                "vehicle_no": getattr(doc, "vehicle_no", None),
                "lock_no": getattr(doc, "lock_no", None),
                "posting_date": getattr(doc, "posting_date", None),
                "posting_time": getattr(doc, "posting_time", None),
                "item_name": getattr(doc, "item_name", None),
                "description": getattr(doc, "description", None),
                "uom": getattr(doc, "uom", None)
            })
            
            # Check if any import receipt fields exist
            if any([row_data.bill_of_entry, row_data.bill_of_entry_date, row_data.assessable_value_inr]):
                bill_of_entry_display = format_bill_of_entry(row_data.bill_of_entry, row_data.bill_of_entry_date)
                # Details of Bond should come directly from bond_doc_type field
                bond_details = row_data.bond_doc_type or ""
                insurance_details = format_insurance_details(row_data.insurance_no, row_data.insurance_date)
                invoice_display = format_invoice(row_data.supplier_invoice_no, row_data.supplier_invoice_date)
                receipt_datetime = format_receipt_datetime(row_data.posting_date, row_data.posting_time)
                
                result.append({
                    "bill_of_entry_no_and_date": bill_of_entry_display,
                    "customs_station": row_data.customs_station or "",
                    "bond_details": bond_details,
                    "insurance_details": insurance_details,
                    "description_of_goods": row_data.description or row_data.item_name or "",
                    "invoice_no_and_date": invoice_display,
                    "quantity_with_uqc": format_quantity_with_uqc(qty, row_data.uom or ""),  # Using stock ledger qty
                    "assessable_value": row_data.assessable_value_inr or 0,
                    "duty_bcd": row_data.basic_custom_duty_inr or 0,
                    "duty_igst": row_data.tax_amount_inr or 0,
                    "duty_comp_cess": row_data.compensation_cess_inr or 0,
                    "registration_no_transport": (row_data.transport_registration_no or row_data.vehicle_no or ""),
                    "lock_no": row_data.lock_no or "",
                    "receipt_date_time": receipt_datetime,
                    "purchase_receipt": docname if doctype == "Purchase Receipt" else ""
                })
    except Exception as e:
        frappe.log_error(f"Error getting source document details: {str(e)}")
    
    return result

def format_bill_of_entry(bill_of_entry, bill_of_entry_date):
    """Format Bill of Entry No. and date"""
    if bill_of_entry and bill_of_entry_date:
        return f"{bill_of_entry} / {frappe.format(bill_of_entry_date, {'fieldtype': 'Date'})}"
    elif bill_of_entry:
        return str(bill_of_entry)
    elif bill_of_entry_date:
        return frappe.format(bill_of_entry_date, {'fieldtype': 'Date'})
    return ""


def format_bond_details(bond_doc_type, bond_posting_date, bond_value, bond_valid_till):
    """Format Bond details"""
    parts = []
    if bond_doc_type:
        parts.append(f"Type: {bond_doc_type}")
    if bond_posting_date:
        parts.append(f"Date: {frappe.format(bond_posting_date, {'fieldtype': 'Date'})}")
    if bond_value:
        parts.append(f"Value: {fmt_money(bond_value, currency='INR')}")
    if bond_valid_till:
        parts.append(f"Valid Till: {frappe.format(bond_valid_till, {'fieldtype': 'Date'})}")
    return " | ".join(parts) if parts else ""


def format_insurance_details(insurance_no, insurance_date):
    """Format Insurance details"""
    if insurance_no and insurance_date:
        return f"{insurance_no} / {frappe.format(insurance_date, {'fieldtype': 'Date'})}"
    elif insurance_no:
        return str(insurance_no)
    elif insurance_date:
        return frappe.format(insurance_date, {'fieldtype': 'Date'})
    return ""


def format_invoice(invoice_no, invoice_date):
    """Format Invoice No. and date"""
    if invoice_no and invoice_date:
        return f"{invoice_no} / {frappe.format(invoice_date, {'fieldtype': 'Date'})}"
    elif invoice_no:
        return str(invoice_no)
    elif invoice_date:
        return frappe.format(invoice_date, {'fieldtype': 'Date'})
    return ""


def format_quantity_with_uqc(qty, uom):
    """Format Quantity with UQC (Unit Quantity Code)"""
    if qty and uom:
        return f"{frappe.format(qty, {'fieldtype': 'Float'})} {uom}"
    elif qty:
        return frappe.format(qty, {'fieldtype': 'Float'})
    return ""


def format_receipt_datetime(posting_date, posting_time=None):
    """Format Date and time of receipt at the warehouse"""
    try:
        if posting_date:
            # If posting_date is already a datetime, use it directly
            if isinstance(posting_date, str) and ' ' in posting_date:
                dt = get_datetime(posting_date)
                return format_datetime(dt, "dd-MM-yyyy HH:mm")
            elif posting_time:
                dt = get_datetime(f"{posting_date} {posting_time}")
                return format_datetime(dt, "dd-MM-yyyy HH:mm")
            else:
                # Try to get time from posting_date if it's a datetime
                dt = get_datetime(posting_date)
                if dt and dt.hour != 0 and dt.minute != 0:
                    return format_datetime(dt, "dd-MM-yyyy HH:mm")
                return frappe.format(posting_date, {'fieldtype': 'Date'})
    except Exception:
        # Fallback to simple date format
        if posting_date:
            return frappe.format(posting_date, {'fieldtype': 'Date'})
    return ""


def get_outward_columns():
    """Get columns for outward/removals report"""
    columns = [
        {
            "label": "Date of issue",
            "fieldname": "goods_date_of_issue",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Description of goods",
            "fieldname": "goods_description",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": "Quantity with UQC",
            "fieldname": "goods_quantity_with_uqc",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Value",
            "fieldname": "goods_value",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Date and time of removal",
            "fieldname": "job_removal_datetime",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Description of goods",
            "fieldname": "job_description",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": "Quantity with UQC",
            "fieldname": "job_quantity_with_uqc",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Value",
            "fieldname": "job_value",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Delivery Challan No.",
            "fieldname": "delivery_challan_no",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Details of Job worker",
            "fieldname": "job_worker_details",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": "GSTIN (if applicable)",
            "fieldname": "job_worker_gstin",
            "fieldtype": "Data",
            "width": 160,
        }
    ]
    
    return columns


def get_columns():
    """Get columns matching Annexure-B format"""
    columns = [
        {
            "label": "Bill of Entry No. and date",
            "fieldname": "bill_of_entry_no_and_date",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": "Customs Station of import",
            "fieldname": "customs_station",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": "Details of Bond",
            "fieldname": "bond_details",
            "fieldtype": "Data",
            "width": 450
        },
        {
            "label": "Details of insurance",
            "fieldname": "insurance_details",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": "Description of goods",
            "fieldname": "description_of_goods",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": "Invoice No. and date",
            "fieldname": "invoice_no_and_date",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": "Quantity with UQC",
            "fieldname": "quantity_with_uqc",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": "Assessable Value",
            "fieldname": "assessable_value",
            "fieldtype": "Currency",
            "options": "INR",
            "width": 130
        },
        {
            "label": "BCD",
            "fieldname": "duty_bcd",
            "fieldtype": "Currency",
            "options": "INR",
            "width": 100
        },
        {
            "label": "IGST",
            "fieldname": "duty_igst",
            "fieldtype": "Currency",
            "options": "INR",
            "width": 100
        },
        {
            "label": "Comp. cess",
            "fieldname": "duty_comp_cess",
            "fieldtype": "Currency",
            "options": "INR",
            "width": 100
        },
        {
            "label": "Registration No. of means of transport",
            "fieldname": "registration_no_transport",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": "One-time Lock no.",
            "fieldname": "lock_no",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Date and time of receipt at the warehouse",
            "fieldname": "receipt_date_time",
            "fieldtype": "Data",
            "width": 220
        },
        {
            "label": "Purchase Receipt",
            "fieldname": "purchase_receipt",
            "fieldtype": "Link",
            "options": "Purchase Receipt",
            "width": 150
        }
    ]
    
    return columns

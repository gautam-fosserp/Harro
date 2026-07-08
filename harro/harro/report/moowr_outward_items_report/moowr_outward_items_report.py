# Copyright (c) 2026, Fosserp and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _

from harro.harro.report.import_receipt.import_receipt import get_data as get_import_receipt_data

_QTY_PREFIX_RE = re.compile(r"^-?\d+(\.\d+)?")


def execute(filters=None):
	filters = filters or {}

	# This report always shows outward removals - it reuses Import
	# Receipt's outward Stock Ledger logic (Delivery Note removals + Stock
	# Entry "Send to Subcontractor", with source-document/batch tracing)
	# but keeps this report's own column layout instead of Import
	# Receipt's outward columns.
	columns = get_outward_columns()
	data = get_outward_data(filters)
	return columns, data


def get_outward_columns():
	return [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Item Name / Description"), "fieldname": "description", "fieldtype": "Data", "width": 220},
		{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Rate in INR"), "fieldname": "rate_inr", "fieldtype": "Currency", "options": "inr_currency", "width": 130},
		{"label": _("Rate in EUR"), "fieldname": "rate_eur", "fieldtype": "Currency", "options": "eur_currency", "width": 130},
		{"label": _("Exchange Rate"), "fieldname": "conversion_rate", "fieldtype": "Float", "width": 120},
		{"label": _("Date of Removal"), "fieldname": "removal_date", "fieldtype": "Data", "width": 160},
		{"label": _("From Warehouse"), "fieldname": "from_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
		{"label": _("To Warehouse"), "fieldname": "to_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
		{"label": _("Outward Document Type"), "fieldname": "outward_reference_doctype", "fieldtype": "Data", "width": 140},
		{
			"label": _("Outward Document Reference"),
			"fieldname": "outward_reference_no",
			"fieldtype": "Dynamic Link",
			"options": "outward_reference_doctype",
			"width": 220,
		},
		{"label": _("Inward Document Type"), "fieldname": "inward_reference_doctype", "fieldtype": "Data", "width": 140},
		{
			"label": _("Inward Document Reference"),
			"fieldname": "inward_reference_no",
			"fieldtype": "Dynamic Link",
			"options": "inward_reference_doctype",
			"width": 200,
		},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 220},
		{"label": _("Purchase Order"), "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 160},
		{"label": _("Material Request"), "fieldname": "material_request", "fieldtype": "Link", "options": "Material Request", "width": 160},
		{"label": _("Supplier Invoice No"), "fieldname": "supplier_invoice_no", "fieldtype": "Data", "width": 160},
		{"label": _("Supplier Invoice Date"), "fieldname": "supplier_invoice_date", "fieldtype": "Date", "width": 150},
		{"label": _("Bill of Entry No"), "fieldname": "bill_of_entry_no", "fieldtype": "Data", "width": 160},
		{"label": _("Bill of Entry Date"), "fieldname": "bill_of_entry_date", "fieldtype": "Date", "width": 150},
		{"label": _("Project (BA Number)"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 160},
		{"label": _("Machine No"), "fieldname": "custom_machine_no", "fieldtype": "Data", "width": 140},
		{"label": _("Machine Description"), "fieldname": "custom_machine_description", "fieldtype": "Data", "width": 220},
	]


def _resolve_warehouses(outward_reference_doctype, outward_reference_no, item_code):
	"""Return (from_warehouse, to_warehouse) for the outward voucher/item.

	- Stock Entry: has real source/target warehouses per item
	  (s_warehouse / t_warehouse on Stock Entry Detail).
	- Delivery Note: goods leave to a customer, not another warehouse, so
	  only the source (from) warehouse applies; to_warehouse is blank.

	`item_code` is tried first (matches the item actually on the outward
	voucher), but for outward rows produced via raw-material batch tracing,
	the row's item_code reflects the *inward* raw material, not the item on
	the outward voucher - so this falls back to the first item row on the
	voucher itself when there's no match, since a Stock Entry / Delivery
	Note typically moves between one consistent warehouse pair.
	"""
	if not outward_reference_doctype or not outward_reference_no:
		return "", ""

	if outward_reference_doctype == "Stock Entry":
		row = None
		if item_code:
			row = frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": outward_reference_no, "item_code": item_code},
				["s_warehouse", "t_warehouse"],
				as_dict=True,
			)
		if not row:
			row = frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": outward_reference_no},
				["s_warehouse", "t_warehouse"],
				as_dict=True,
				order_by="idx asc",
			)
		if row:
			return row.s_warehouse or "", row.t_warehouse or ""
		return "", ""

	if outward_reference_doctype == "Delivery Note":
		from_warehouse = None
		if item_code:
			from_warehouse = frappe.db.get_value(
				"Delivery Note Item",
				{"parent": outward_reference_no, "item_code": item_code},
				"warehouse",
			)
		if not from_warehouse:
			from_warehouse = frappe.db.get_value(
				"Delivery Note Item",
				{"parent": outward_reference_no},
				"warehouse",
				order_by="idx asc",
			)
		return from_warehouse or "", ""

	return "", ""


def _resolve_outward_project_and_machine(outward_reference_doctype, outward_reference_no, inward_reference_doctype, inward_reference_no):
	"""Return (project, machine_no, machine_description) for an outward row.

	Tries the outward voucher's own project first (Stock Entry / Delivery
	Note both carry a project field directly); falls back to the inward
	Purchase Receipt's project when the outward voucher has none set.
	Machine No / Description both come from the resolved Project, same as
	the inward view.
	"""
	project = None

	if outward_reference_doctype and outward_reference_no:
		project = frappe.db.get_value(outward_reference_doctype, outward_reference_no, "project")

	if not project and inward_reference_doctype == "Purchase Receipt" and inward_reference_no:
		project = frappe.db.get_value("Purchase Receipt", inward_reference_no, "project")

	if not project:
		return "", "", ""

	proj = frappe.db.get_value("Project", project, ["custom_machine_no", "custom_machine_description"], as_dict=True)
	if not proj:
		return project, "", ""

	return project, proj.custom_machine_no or "", proj.custom_machine_description or ""


def _resolve_rates(inward_reference_doctype, inward_reference_no, item_code):
	"""Return (rate_inr, rate_eur, conversion_rate) sourced from the inward
	document's own item row - base_rate for INR, rate for EUR (only when
	that document's currency is EUR) - matching how the inward view
	resolves rates.

	Stock Entry has no purchase currency/rate/exchange-rate concept (it
	only has basic_rate, always in company currency), so rate_eur and
	conversion_rate are only ever populated when the inward reference is a
	Purchase Receipt.
	"""
	if not inward_reference_no:
		return None, None, None

	if inward_reference_doctype == "Purchase Receipt":
		pr = frappe.db.get_value("Purchase Receipt", inward_reference_no, ["currency", "conversion_rate"], as_dict=True)
		pr_currency = pr.currency if pr else None

		row = None
		if item_code:
			row = frappe.db.get_value(
				"Purchase Receipt Item",
				{"parent": inward_reference_no, "item_code": item_code},
				["base_rate", "rate"],
				as_dict=True,
			)
		if not row:
			row = frappe.db.get_value(
				"Purchase Receipt Item",
				{"parent": inward_reference_no},
				["base_rate", "rate"],
				as_dict=True,
				order_by="idx asc",
			)
		if not row:
			return None, None, None

		is_eur = pr_currency == "EUR"
		rate_eur = row.rate if is_eur else None
		conversion_rate = pr.conversion_rate if (is_eur and pr) else None
		return row.base_rate, rate_eur, conversion_rate

	if inward_reference_doctype == "Stock Entry":
		row = None
		if item_code:
			row = frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": inward_reference_no, "item_code": item_code},
				"basic_rate",
			)
		if row is None:
			row = frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": inward_reference_no},
				"basic_rate",
				order_by="idx asc",
			)
		return row, None, None

	return None, None, None


def _resolve_supplier(inward_reference_doctype, inward_reference_no):
	"""Return the supplier on the inward document - Purchase Receipt has a
	direct supplier field; Stock Entry (Material Receipt) may have one too
	when goods were received directly via Stock Entry."""
	if not inward_reference_doctype or not inward_reference_no:
		return ""

	if inward_reference_doctype in ("Purchase Receipt", "Stock Entry"):
		return frappe.db.get_value(inward_reference_doctype, inward_reference_no, "supplier") or ""

	return ""


def _resolve_po_and_material_request(inward_reference_doctype, inward_reference_no, item_code):
	"""Return (purchase_order, material_request) traced from the inward
	Purchase Receipt's item row (matching item_code where possible, else
	the PR's first item row)."""
	if inward_reference_doctype != "Purchase Receipt" or not inward_reference_no:
		return "", ""

	row = None
	if item_code:
		row = frappe.db.get_value(
			"Purchase Receipt Item",
			{"parent": inward_reference_no, "item_code": item_code},
			["purchase_order", "material_request"],
			as_dict=True,
		)
	if not row:
		row = frappe.db.get_value(
			"Purchase Receipt Item",
			{"parent": inward_reference_no},
			["purchase_order", "material_request"],
			as_dict=True,
			order_by="idx asc",
		)
	if not row:
		return "", ""

	material_request = row.material_request
	if not material_request and row.purchase_order:
		material_request = frappe.db.get_value("Purchase Order Item", {"parent": row.purchase_order}, "material_request")

	return row.purchase_order or "", material_request or ""


def get_outward_data(filters):
	# Import Receipt's get_data() branches on show_outward internally; this
	# report has no such checkbox and always wants the outward branch.
	filters = dict(filters or {})
	filters["show_outward"] = 1

	raw_rows = get_import_receipt_data(filters)
	if not raw_rows:
		return []

	is_stock_item_cache = {}

	# Merge rows for the same item removed via multiple batches within the
	# same outward voucher into a single row with summed Out Qty, instead
	# of one row per batch consumed.
	merged = {}
	order = []

	for raw in raw_rows:
		row = frappe._dict(raw)

		item_code = row.get("item_code", "")

		# Always restrict to stock items - non-stock items don't carry
		# meaningful outward removal data for this report.
		if item_code:
			if item_code not in is_stock_item_cache:
				is_stock_item_cache[item_code] = frappe.db.get_value("Item", item_code, "is_stock_item")
			if not is_stock_item_cache[item_code]:
				continue

		# Different code paths in Import Receipt use either "quantity" or
		# "quantity_with_uqc" for the same formatted string (e.g. "100 Nos").
		quantity_str = str(row.get("quantity", row.get("quantity_with_uqc", "")) or "")
		qty_match = _QTY_PREFIX_RE.match(quantity_str.strip())
		out_qty = float(qty_match.group()) if qty_match else 0.0

		if row.get("inward_reference_doctype") and row.get("inward_reference_no"):
			inward_reference_doctype = row.get("inward_reference_doctype")
			inward_reference_no = row.get("inward_reference_no")
		elif row.get("purchase_receipt"):
			inward_reference_doctype = "Purchase Receipt"
			inward_reference_no = row.get("purchase_receipt")
		elif row.get("stock_entry"):
			inward_reference_doctype = "Stock Entry"
			inward_reference_no = row.get("stock_entry")
		else:
			inward_reference_doctype = ""
			inward_reference_no = ""

		outward_reference_doctype = row.get("outward_reference_doctype", "")
		outward_reference_no = row.get("outward_reference_no", "")

		# One merged row per item + outward voucher (collapses multiple
		# batches of the same item consumed by the same removal).
		merge_key = (item_code, outward_reference_doctype, outward_reference_no)

		if merge_key in merged:
			merged[merge_key]["out_qty"] += out_qty
			continue

		from_warehouse, to_warehouse = _resolve_warehouses(
			outward_reference_doctype, outward_reference_no, item_code
		)
		project, machine_no, machine_description = _resolve_outward_project_and_machine(
			outward_reference_doctype, outward_reference_no, inward_reference_doctype, inward_reference_no
		)
		purchase_order, material_request = _resolve_po_and_material_request(
			inward_reference_doctype, inward_reference_no, item_code
		)

		bill_of_entry_no = ""
		bill_of_entry_date = None
		supplier_invoice_no = ""
		supplier_invoice_date = None
		if inward_reference_doctype == "Purchase Receipt" and inward_reference_no:
			pr_row = frappe.db.get_value(
				"Purchase Receipt",
				inward_reference_no,
				["custom_bill_of_entry_no", "custom_bill_of_entry_date", "supplier_invoice_no", "supplier_invoice_date"],
				as_dict=True,
			)
			if pr_row:
				bill_of_entry_no = pr_row.custom_bill_of_entry_no or ""
				bill_of_entry_date = pr_row.custom_bill_of_entry_date
				supplier_invoice_no = pr_row.supplier_invoice_no or ""
				supplier_invoice_date = pr_row.supplier_invoice_date

		rate_inr, rate_eur, conversion_rate = _resolve_rates(inward_reference_doctype, inward_reference_no, item_code)
		supplier = _resolve_supplier(inward_reference_doctype, inward_reference_no)

		removal_date_raw = str(row.get("removal_date", row.get("receipt_date_time", "")) or "")
		# Show date only, no time (e.g. "31-03-2026 12:01" -> "31-03-2026").
		removal_date = removal_date_raw.split(" ")[0] if removal_date_raw else ""

		merged[merge_key] = {
			"item_code": item_code,
			"description": row.get("description", row.get("description_of_goods", "")),
			"out_qty": out_qty,
			"rate_inr": rate_inr,
			"rate_eur": rate_eur,
			"conversion_rate": conversion_rate,
			"inr_currency": "INR",
			"eur_currency": "EUR",
			"removal_date": removal_date,
			"supplier": supplier,
			"from_warehouse": from_warehouse,
			"to_warehouse": to_warehouse,
			"outward_reference_doctype": outward_reference_doctype,
			"outward_reference_no": outward_reference_no,
			"inward_reference_doctype": inward_reference_doctype,
			"inward_reference_no": inward_reference_no,
			"purchase_order": purchase_order,
			"material_request": material_request,
			"supplier_invoice_no": supplier_invoice_no,
			"supplier_invoice_date": supplier_invoice_date,
			"bill_of_entry_no": bill_of_entry_no,
			"bill_of_entry_date": bill_of_entry_date,
			"project": project,
			"custom_machine_no": machine_no,
			"custom_machine_description": machine_description,
		}
		order.append(merge_key)

	return [merged[key] for key in order]



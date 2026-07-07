# Copyright (c) 2026, Fosserp and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("PO Name"), "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 140},
		{"label": _("PO Date"), "fieldname": "po_date", "fieldtype": "Date", "width": 100},
		{"label": _("Purchase Receipt"), "fieldname": "purchase_receipt", "fieldtype": "Link", "options": "Purchase Receipt", "width": 140},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
		{"label": _("Bill of Entry No"), "fieldname": "bill_of_entry_no", "fieldtype": "Data", "width": 140},
		{"label": _("Bill of Entry Date"), "fieldname": "bill_of_entry_date", "fieldtype": "Date", "width": 130},
		{"label": _("Material Request"), "fieldname": "material_request", "fieldtype": "Link", "options": "Material Request", "width": 140},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("Rate in INR"), "fieldname": "rate_inr", "fieldtype": "Currency", "options": "inr_currency", "width": 110},
		{"label": _("Rate in EUR"), "fieldname": "rate_eur", "fieldtype": "Currency", "options": "eur_currency", "width": 110},
		{"label": _("Amount in INR"), "fieldname": "amount_inr", "fieldtype": "Currency", "options": "inr_currency", "width": 120},
		{"label": _("Amount in EUR"), "fieldname": "amount_eur", "fieldtype": "Currency", "options": "eur_currency", "width": 120},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 130},
		{"label": _("Rack"), "fieldname": "rack", "fieldtype": "Link", "options": "Rack", "width": 100},
		{"label": _("Bin Location"), "fieldname": "bin_location", "fieldtype": "Link", "options": "Bin Location", "width": 120},
		{"label": _("Project (BA Number)"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
		{"label": _("Machine No"), "fieldname": "custom_machine_no", "fieldtype": "Data", "width": 120},
		{"label": _("Machine Description"), "fieldname": "custom_machine_description", "fieldtype": "Data", "width": 180},
	]


def get_conditions(filters):
	conditions = []
	values = {}

	if filters.get("company"):
		conditions.append("pr.company = %(company)s")
		values["company"] = filters.get("company")

	if filters.get("from_date"):
		conditions.append("pr.posting_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("pr.posting_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	if filters.get("purchase_order"):
		conditions.append("pr_item.purchase_order = %(purchase_order)s")
		values["purchase_order"] = filters.get("purchase_order")

	if filters.get("purchase_receipt"):
		conditions.append("pr.name = %(purchase_receipt)s")
		values["purchase_receipt"] = filters.get("purchase_receipt")

	if filters.get("project"):
		conditions.append("(pr.project = %(project)s OR po.project = %(project)s)")
		values["project"] = filters.get("project")

	if filters.get("supplier"):
		conditions.append("pr.supplier = %(supplier)s")
		values["supplier"] = filters.get("supplier")

	condition_str = " AND " + " AND ".join(conditions) if conditions else ""
	return condition_str, values


def get_data(filters):
	conditions, values = get_conditions(filters)

	query = f"""
		SELECT
			pr_item.purchase_order AS purchase_order,
			po.transaction_date AS po_date,
			pr.name AS purchase_receipt,
			pr.supplier AS supplier,
			pr.custom_bill_of_entry_no AS bill_of_entry_no,
			pr.custom_bill_of_entry_date AS bill_of_entry_date,
			COALESCE(pr_item.material_request, po_item.material_request) AS material_request,
			pr_item.item_code AS item_code,
			pr_item.item_name AS item_name,
			pr_item.qty AS qty,
			pr_item.base_rate AS rate_inr,
			CASE WHEN pr.currency = 'EUR' THEN pr_item.rate ELSE NULL END AS rate_eur,
			'INR' AS inr_currency,
			'EUR' AS eur_currency,
			pr_item.base_amount AS amount_inr,
			CASE WHEN pr.currency = 'EUR' THEN pr_item.amount ELSE NULL END AS amount_eur,
			pr_item.warehouse AS warehouse,
			pr_item.rack AS rack,
			pr_item.bin_location AS bin_location,
			COALESCE(pr.project, po.project) AS project,
			proj.custom_machine_no AS custom_machine_no,
			proj.custom_machine_description AS custom_machine_description
		FROM `tabPurchase Receipt Item` pr_item
		INNER JOIN `tabPurchase Receipt` pr ON pr.name = pr_item.parent
		LEFT JOIN `tabPurchase Order` po ON po.name = pr_item.purchase_order
		LEFT JOIN `tabPurchase Order Item` po_item ON po_item.name = pr_item.purchase_order_item
		LEFT JOIN `tabProject` proj ON proj.name = COALESCE(pr.project, po.project)
		WHERE pr.docstatus = 1
		{conditions}
		ORDER BY pr.posting_date DESC, pr.name, pr_item.idx
	"""

	return frappe.db.sql(query, values, as_dict=True)

# Copyright (c) 2026, Fosserp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import today
from erpnext.stock.get_item_details import get_item_details


class VisaRequest(Document):
	pass


@frappe.whitelist()
def get_visa_check_list_details(chekck_list):
	return frappe.get_doc("Country Wise visa Document Checklist", chekck_list)



def add_item(source, target, source_parent):
	if not target.company:
		target.company = frappe.defaults.get_user_default("Company")

	if not target.posting_date:
		target.posting_date = today()

	if not target.currency:
		target.currency = frappe.get_cached_value("Company", target.company, "default_currency")

	if not target.conversion_rate:
		target.conversion_rate = 1

	if source.custom_service_type:
		args = {
			"item_code": source.custom_service_type,
			"doctype": "Purchase Invoice",
			"company": target.company,
			"supplier": target.supplier,
			"posting_date": target.posting_date,
			"currency": target.currency,
			"conversion_rate": target.conversion_rate,
			"price_list": None,
			"qty": 1,
			"ignore_pricing_rule": 1,
		}

		item_details = get_item_details(args)

		qty = 1
		custom_rate = source.custom_cost or 0

		target.append("items", {
			"item_code": source.custom_service_type,
			"item_name": item_details.item_name,
			"description": item_details.description,
			"uom": item_details.uom,
			"qty": qty,
			"price_list_rate": 0,
			"rate": custom_rate,
			"amount": qty * custom_rate,
			"discount_percentage": 0,

			"expense_account": item_details.expense_account
		})



@frappe.whitelist()
def create_purchase_invoice(source_name, target_doc=None):
	doclist = get_mapped_doc(
		"Visa Request",
		source_name,
		{
			"Visa Request": {
				"doctype": "Purchase Invoice", 
				"field_map" : {
					"name" : "visa_request",
					"custom_vendor_name": "supplier",
					"custom_vendor_invoice": "custom_supplier_invoice",
					"custom_supplier_invoice_no": "bill_no"
				},
				"postprocess": add_item
			},
		},
		target_doc,
	)
	doclist.run_method("set_missing_values")
	doclist.run_method("calculate_taxes_and_totals")

	return doclist
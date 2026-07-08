// Copyright (c) 2026, Fosserp and contributors
// For license information, please see license.txt

frappe.query_reports["MOOWR Inward Items Report"] = {
	filters: [
		{
			fieldname: "company",
			label: "Company",
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: "From Date",
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "purchase_order",
			label: "Purchase Order",
			fieldtype: "Link",
			options: "Purchase Order",
			depends_on: "eval:!doc.show_outward",
		},
		{
			fieldname: "purchase_receipt",
			label: "Purchase Receipt",
			fieldtype: "Link",
			options: "Purchase Receipt",
			depends_on: "eval:!doc.show_outward",
		},
		{
			fieldname: "project",
			label: "Project",
			fieldtype: "Link",
			options: "Project",
			depends_on: "eval:!doc.show_outward",
		},
		{
			fieldname: "supplier",
			label: "Supplier",
			fieldtype: "Link",
			options: "Supplier",
			depends_on: "eval:!doc.show_outward",
		},
		{
			fieldname: "warehouse",
			label: "Warehouse",
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function() {
				return {
					filters: {
						company: frappe.query_report.get_filter_value("company")
					}
				};
			},
		},
		{
			fieldname: "show_outward",
			label: __("Show Outward"),
			fieldtype: "Check",
			default: 0,
			description: __("Show outward removals (Delivery Note / Send to Subcontractor Stock Entries) instead of inward Purchase Receipt items, with reference to the source inward document and batch."),
		},
		{
			fieldname: "external_only",
			label: __("External Transfer Only"),
			fieldtype: "Check",
			default: 0,
			depends_on: "eval:doc.show_outward",
			description: __("When checked, only Send to Subcontractor (external removal) Stock Entries are shown. When unchecked, internal transfers (Material Transfer, Material Transfer for Manufacture, Manufacture) are also included."),
		},
		{
			fieldname: "only_stock_items",
			label: __("Show Only Stock Items"),
			fieldtype: "Check",
			default: 0,
			description: __("When checked, only items marked as Stock Item on the Item master are shown."),
		},
	],
};

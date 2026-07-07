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
		},
		{
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date",
		},
		{
			fieldname: "purchase_order",
			label: "Purchase Order",
			fieldtype: "Link",
			options: "Purchase Order",
		},
		{
			fieldname: "purchase_receipt",
			label: "Purchase Receipt",
			fieldtype: "Link",
			options: "Purchase Receipt",
		},
		{
			fieldname: "project",
			label: "Project",
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "supplier",
			label: "Supplier",
			fieldtype: "Link",
			options: "Supplier",
		},
	],
};

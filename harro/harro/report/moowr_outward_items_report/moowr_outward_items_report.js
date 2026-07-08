// Copyright (c) 2026, Fosserp and contributors
// For license information, please see license.txt

frappe.query_reports["MOOWR Outward Items Report"] = {
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
	],
};

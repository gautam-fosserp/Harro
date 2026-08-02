// Copyright (c) 2026, Fosserp and contributors
// For license information, please see license.txt

frappe.query_reports["FTE Utilization Summary"] = {
	"filters": [
		{
			"label": "Department",
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department"
		},
		{
			"label": "Employee",
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"label": "BA Number",
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"label": "From Date",
			"fieldname": "from_date",
			"fieldtype": "Date",
		},
		{
			"label": "To Date",
			"fieldname": "to_date",
			"fieldtype": "Date"
		}
	]
};

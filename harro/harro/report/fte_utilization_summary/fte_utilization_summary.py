# Copyright (c) 2026, Fosserp and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	return [
		{"label": _("Timesheet"), "fieldtype": "Link", "fieldname": "timesheet", "options": "Timesheet"},
		{"label": _("Department"), "fieldtype": "Link", "fieldname": "department", "options": "Department", "width": 200},
		{"label": _("Employee"), "fieldtype": "Link", "fieldname": "employee", "options": "Employee", "width": 130},
		{"label": _("FTE"), "fieldtype": "Float", "fieldname": "fte", "precision": 2},
		{"label": _("Projects/Tasks"), "fieldtype": "Link", "fieldname": "project", "options": "Project"},
		{"label": _("Actual Hours"), "fieldtype": "Float", "fieldname": "total_hours"},
		{"label": _("Jan"), "fieldtype": "Float", "fieldname": "jan", "precision": 2},
		{"label": _("Feb"), "fieldtype": "Float", "fieldname": "feb", "precision": 2},
		{"label": _("Mar"), "fieldtype": "Float", "fieldname": "mar", "precision": 2},
		{"label": _("Apr"), "fieldtype": "Float", "fieldname": "apr", "precision": 2},
		{"label": _("May"), "fieldtype": "Float", "fieldname": "may", "precision": 2},
		{"label": _("Jun"), "fieldtype": "Float", "fieldname": "jun", "precision": 2},
		{"label": _("Jul"), "fieldtype": "Float", "fieldname": "jul", "precision": 2},
		{"label": _("Aug"), "fieldtype": "Float", "fieldname": "aug", "precision": 2},
		{"label": _("Sep"), "fieldtype": "Float", "fieldname": "sep", "precision": 2},
		{"label": _("Oct"), "fieldtype": "Float", "fieldname": "oct", "precision": 2},
		{"label": _("Nov"), "fieldtype": "Float", "fieldname": "nov", "precision": 2},
		{"label": _("Dec"), "fieldtype": "Float", "fieldname": "dec", "precision": 2},
	]


def get_conditions(filters):
	conditions = ""
	if filters.get("from_date"):
		conditions += " AND tsd.from_time >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " AND tsd.from_time <= %(to_date)s"
	if filters.get("department"):
		conditions += " AND ts.department = %(department)s"
	if filters.get("employee"):
		conditions += " AND ts.employee = %(employee)s"
	if filters.get("project"):
		conditions += " AND tsd.project = %(project)s"
	return conditions


def get_data(filters):
	conditions = get_conditions(filters)

	data = frappe.db.sql(f"""
		SELECT
			ts.name as timesheet,
			ts.department AS department,
			ts.employee AS employee,
			1680 AS fte,
			tsd.project AS project,
			SUM(tsd.hours) AS total_hours,
			SUM(CASE WHEN MONTH(tsd.from_time) = 1  THEN tsd.hours ELSE 0 END) AS jan,
			SUM(CASE WHEN MONTH(tsd.from_time) = 2  THEN tsd.hours ELSE 0 END) AS feb,
			SUM(CASE WHEN MONTH(tsd.from_time) = 3  THEN tsd.hours ELSE 0 END) AS mar,
			SUM(CASE WHEN MONTH(tsd.from_time) = 4  THEN tsd.hours ELSE 0 END) AS apr,
			SUM(CASE WHEN MONTH(tsd.from_time) = 5  THEN tsd.hours ELSE 0 END) AS may,
			SUM(CASE WHEN MONTH(tsd.from_time) = 6  THEN tsd.hours ELSE 0 END) AS jun,
			SUM(CASE WHEN MONTH(tsd.from_time) = 7  THEN tsd.hours ELSE 0 END) AS jul,
			SUM(CASE WHEN MONTH(tsd.from_time) = 8  THEN tsd.hours ELSE 0 END) AS aug,
			SUM(CASE WHEN MONTH(tsd.from_time) = 9  THEN tsd.hours ELSE 0 END) AS sep,
			SUM(CASE WHEN MONTH(tsd.from_time) = 10 THEN tsd.hours ELSE 0 END) AS oct,
			SUM(CASE WHEN MONTH(tsd.from_time) = 11 THEN tsd.hours ELSE 0 END) AS nov,
			SUM(CASE WHEN MONTH(tsd.from_time) = 12 THEN tsd.hours ELSE 0 END) AS `dec`
		FROM 
			`tabTimesheet Detail` tsd
		INNER JOIN 
			`tabTimesheet` ts ON ts.name = tsd.parent
		WHERE 
			ts.docstatus < 2 {conditions}
		GROUP BY 
			ts.employee, tsd.project, ts.employee
		ORDER BY 
			ts.department, ts.employee, tsd.project
	""", filters, as_dict=True)

	return data



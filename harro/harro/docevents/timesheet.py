import frappe
from harro.harro.docevents.project import calculate_timesheet_hours


def validate(self, method):
    if self.parent_project:
        calculate_timesheet_hours(self.parent_project)

def on_submit(self, method):
    if self.parent_project:
        calculate_timesheet_hours(self.parent_project)


def on_cancel(self, method):
    if self.parent_project:
        calculate_timesheet_hours(self.parent_project)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_employee_wise_activity(doctype, txt, searchfield, start, page_len, filters):
    employee = filters.get("employee")
    department = frappe.db.get_value("Employee", employee, "custom_department_for_timesheet") if employee else None
    conditions = ""
    values = {"txt": "%{}%".format(txt), "start": start, "page_len": page_len}
    if department:
        conditions = "and custom_department_for_timesheet = %(department)s"
        values["department"] = department

    return frappe.db.sql(f"""
        select name, activity_type
        from `tabActivity Type`
        where (name like %(txt)s or activity_type like %(txt)s)
        {conditions}
        limit %(page_len)s offset %(start)s
    """, values)

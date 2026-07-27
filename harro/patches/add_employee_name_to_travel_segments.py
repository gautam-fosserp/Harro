import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields(
        {
            "Travel Flight Details": [
                {
                    "fieldname": "employee_name",
                    "label": "Employee Name",
                    "fieldtype": "Data",
                    "insert_after": "employee",
                    "fetch_from": "employee.employee_name",
                    "read_only": 1,
                    "in_list_view": 1,
                }
            ],
            "Travel Hotel Booking": [
                {
                    "fieldname": "employee_name",
                    "label": "Employee Name",
                    "fieldtype": "Data",
                    "insert_after": "employee",
                    "fetch_from": "employee.employee_name",
                    "read_only": 1,
                    "in_list_view": 1,
                }
            ],
        }
    )

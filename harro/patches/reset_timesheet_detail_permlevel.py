import frappe


def execute():
    fields = ["from_time", "to_time", "activity_type", "employee"]
    for fieldname in fields:
        existing = frappe.db.exists(
            "Property Setter",
            {"doc_type": "Timesheet Detail", "field_name": fieldname, "property": "permlevel"},
        )
        if existing:
            frappe.db.set_value("Property Setter", existing, "value", "0")
        else:
            frappe.make_property_setter(
                {
                    "doctype": "Timesheet Detail",
                    "fieldname": fieldname,
                    "property": "permlevel",
                    "value": 0,
                    "property_type": "Int",
                },
                validate_fields_for_doctype=False,
            )
    frappe.clear_cache(doctype="Timesheet Detail")
    frappe.clear_cache(doctype="Task")

import frappe


def execute():
    doc_type = "Travel Planning Employee Details"
    field_name = "custom_status"
    name = f"{doc_type}-{field_name}"

    if not frappe.db.exists("Custom Field", name):
        return

    frappe.db.set_value("Custom Field", name, {"hidden": 1, "in_list_view": 0})
    frappe.clear_cache(doctype=doc_type)

import frappe


def execute():
    doc_type = "Travel Planning Employee Details"
    fields = ["extra_baggage", "mode_of_travel", "travel_to", "travel_from"]

    for field_name in fields:
        name = f"{doc_type}-{field_name}-in_list_view"
        if frappe.db.exists("Property Setter", name):
            continue

        frappe.get_doc(
            {
                "doctype": "Property Setter",
                "doctype_or_field": "DocField",
                "doc_type": doc_type,
                "field_name": field_name,
                "property": "in_list_view",
                "property_type": "Check",
                "value": "0",
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()

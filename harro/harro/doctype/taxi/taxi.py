# Copyright (c) 2025, Fosserp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class Taxi(Document):
    def before_insert(self):
        if self.taxi_requestor:
            return

        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user},["name", "employee_name", "user_id"],as_dict=True)

        if employee:
            self.taxi_requestor = employee.name
            self.taxi_requester_name = employee.employee_name
            self.taxi_requester_email = employee.user_id

@frappe.whitelist()
def create_purchase_invoice(source_name, target_doc=None):

    def update_item_price(item_code, rate):
        """Update existing Item Price(s) for this item to match invoice rate."""
        existing_prices = frappe.get_all(
            "Item Price",
            filters={"item_code": item_code, "buying": 1},
            fields=["name", "price_list"],
        )

        if existing_prices:
            for ip in existing_prices:
                frappe.db.set_value("Item Price", ip.name, "price_list_rate", rate)

    def set_missing_values(source, target):
        item = frappe.get_cached_doc("Item", source.custom_service_item)
        rate = source.cost

        # update item price BEFORE building the item row, so the client
        # doesn't overwrite the rate when the form loads
        update_item_price(item.name, rate)

        target.append("items", {
            "item_code": source.custom_service_item,
            "item_name": item.item_name,
            "uom": item.purchase_uom or item.stock_uom,
            "stock_uom": item.stock_uom,
            "conversion_factor": 1,
            "qty": 1,
            "rate": rate,
            "price_list_rate": rate,
            "cost_center": "Main - Harro IN",
        })

    doclist = get_mapped_doc(
        "Taxi",
        source_name,
        {
            "Taxi": {
                "doctype": "Purchase Invoice",
                "field_map": {
                    "name": "taxi",
                    "custom_taxi_vendor": "supplier",
                    "custom_bill_no": "bill_no",
                },
            },
        },
        target_doc,
        postprocess=set_missing_values,
    )
    return doclist
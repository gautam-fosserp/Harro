# Copyright (c) 2026, Fosserp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TravelFlightDetails(Document):
	pass


@frappe.whitelist()
def add_travel_date_comment(
    docname,
    field_name,
    old_value,
    new_value,
    comment
):

    doc = frappe.get_doc("Travel Flight Details", docname)

    old_value = old_value or "Blank"
    new_value = new_value or "Blank"

    doc.add_comment(
        "Comment",
        f"""
<b>{field_name}</b> was modified from <b>{old_value}</b> to <b>{new_value}</b>.
<br><br>
<b>Reason:</b> {comment}
"""
    )
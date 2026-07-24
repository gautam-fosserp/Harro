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


@frappe.whitelist()
def send_rescheduling_invoice_email(docname, invoice_type):
    doc = frappe.get_doc("Travel Flight Details", docname)

    # Get all enabled users with role "Accounts User" or "Accounts Manager"
    accounts_users = frappe.get_all(
        "Has Role",
        filters={
            "role": ["in", ["Accounts User", "Accounts Manager"]],
            "parenttype": "User",
        },
        fields=["parent"],
    )

    recipients = list(set(
        u.parent for u in accounts_users
        if u.parent not in ("Administrator", "Guest")
    ))

    # Optionally restrict to enabled users only
    if recipients:
        enabled_users = frappe.get_all(
            "User",
            filters={"name": ["in", recipients], "enabled": 1},
            pluck="name",
        )
        recipients = enabled_users

    if not recipients:
        frappe.throw("No users found with role Accounts User or Accounts Manager.")

    if invoice_type == "first":
        file_url = doc.custom_rescheduling_invoice
        label = "First Rescheduling Invoice"
    elif invoice_type == "second":
        file_url = doc.custom_second_rescheduling_invoice
        label = "Second Rescheduling Invoice"
    else:
        frappe.throw("Invalid invoice type")

    if not file_url:
        frappe.throw(f"Please attach the {label} before sending the email.")

    file_doc = frappe.get_doc("File", {"file_url": file_url})

    subject = f"{label} - {doc.employee} ({doc.travel_planning})"
    message = f"""
        Dear Accounts Team,<br><br>
        Please find attached the {label.lower()} for
        <b>{doc.employee}</b> (Travel Planning: {doc.travel_planning}).<br><br>
        Regards,<br>{frappe.session.user}
    """

    frappe.logger().info("Before sendmail")

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        attachments=[{"fid": file_doc.name}],
    )

    frappe.logger().info("After sendmail")

    return True
# Copyright (c) 2026, Fosserp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url_to_form



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

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        attachments=[{"fid": file_doc.name}],
    )

    return True

@frappe.whitelist()
def send_reschedule_ticket(docname, request_type):
    doc = frappe.get_doc("Travel Flight Details", docname)
    travel_planning_url = get_url_to_form("Travel Planning", doc.travel_planning)

    if not doc.contact_email:
            frappe.throw("Traveller email is not set.")
    
    recipients = [doc.contact_email]

    attachments = []

    if request_type == "first":
        subject = f"{doc.employee_name}: Revised Flight Ticket - First Rescheduling"
        message = f"""
            Dear {doc.employee_name}<br><br>
            Your flight ticket has been revised. Please find the updated ticket attached for your reference.<br>
            Kindly review the travel details and contact the travel team if you require any assistance.<br>
            <a href="{travel_planning_url}">Open Travel Planning</a><br><br>
            Thank you, and have a safe journey.<br><br>
            Regards,<br>
            Travel Team
        """

        ticket = doc.custom_rescheduled_flight_ticket
        
    elif request_type == "second":
        subject = f"{doc.employee_name}: Revised Flight Ticket - Second Rescheduling"
        message = f"""
            Dear {doc.employee_name}<br><br>
            Your flight ticket has been rescheduled again. Please find the latest revised ticket attached.<br>
            Kindly review the updated travel details. If you have any questions or need any assistance, please contact the Travel Team<br>
            <a href="{travel_planning_url}">Open Travel Planning</a><br><br>
            Thank you<br><br>
            Regards,<br>
            Travel Team
        """

        ticket = doc.custom_second_rescheduled_flight_ticket
    else:
        frappe.throw("Invalid request type")

    # attach the ticket
    if ticket:
        file_doc = frappe.get_doc("File", {"file_url": ticket})
        attachments.append({
            "fname": file_doc.file_name,
            "fcontent": file_doc.get_content()
        })

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        attachments=attachments,
    )

    return True


@frappe.whitelist()
def send_credit_note_email(docname):
    doc = frappe.get_doc("Travel Flight Details", docname)

    if not doc.custom_credit_note:
        frappe.throw("Please attach the Credit Note before sending the email.")
    if not doc.contact_email:
        frappe.throw("Employee Contact Email is missing on this record.")

    file_doc = frappe.get_doc("File", {"file_url": doc.custom_credit_note})

    # generate clickable link to the current travel flight details document
    travel_flight_details_url = frappe.utils.get_url_to_form("Travel Flight Details", doc.name)

    subject = f"Credit Note Issued for Cancelled Flight- Travel Planning ({doc.travel_planning})"
    message = f"""
        Hello Accounts Team,<br><br>
        This is to inform you that a credit note has been issued for the cancelled flight
        against <b>Travel Flight Details <a href="{travel_flight_details_url}">{doc.name}</a></b>.<br><br>
        Please find the credit note attached for your reference.<br><br>
        Regards,<br>Travel Manager
    """

    frappe.sendmail(
        recipients=[doc.contact_email],
        subject=subject,
        message=message,
        attachments=[{"fid": file_doc.name}],
    )

    return True


@frappe.whitelist()
def send_reschedule_request(docname, request_type):
    doc = frappe.get_doc("Travel Flight Details", docname)
    travel_planning_url = get_url_to_form("Travel Planning", doc.travel_planning)
    travel_flight_details_url = frappe.utils.get_url_to_form("Travel Flight Details", doc.name)

    recipients = []
    # get all user having the Travel Manager Role
    travel_managers = frappe.get_all(
        "Has Role",
        filters={
            "role": "Travel Manager"
        },
        fields=["parent"]
    )

    #Add travel manager email addresses
    for manager in travel_managers:
        user = frappe.db.get_value(
            "User",
            {
                "name": manager.parent,
                "enabled": 1
            },
            "email"
        )

        if user:
            recipients.append(user)

        # Remove duplicate email addresses
        recipients = list(set(recipients))

    if request_type == "first":
        subject = f"Travel Planning {doc.travel_planning} - First Rescheduling Request for {doc.employee_name}"
        message = f"""
            Dear Travel Mannager,<br><br>
            This is to inform you that a first rescheduling request has been updated for <b>{doc.employee_name}</b> under Travel Planning {doc.travel_planning}.<br>
            Kindly review the rescheduled travel details and proceed with the necessary actions.<br>
            <a href="{travel_planning_url}">Open Travel Planning</a><br><br>
            <a href="{travel_flight_details_url}">Click here to view the details</a><br><br>
            Regards,<br>
            {frappe.db.get_value("User", doc.owner, "full_name")}
        """
        
    elif request_type == "second":
        subject = f"Travel Planning {doc.travel_planning} - Second Rescheduling Request for {doc.employee_name}"
        message = f"""
            Dear Travel Manager<br><br>
            This is to inform you that a second rescheduling request has been updated for <b>{doc.employee_name}</b> under Travel Planning {doc.travel_planning}.<br>
            Kindly review the rescheduled travel details and proceed with the necessary actions.<br>
            <a href="{travel_planning_url}">Open Travel Planning</a><br><br>
            <a href="{travel_flight_details_url}">Click here to view the details</a><br><br>
            Thank you<br><br>
            Regards,<br>
            {frappe.db.get_value("User", doc.owner, "full_name")}
        """
    else:
        frappe.throw("Invalid request type")


    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message
    )
    return True

from frappe.model.mapper import get_mapped_doc
@frappe.whitelist()
def make_onward_flight_purchase_invoice(source_name):
    def get_missing_values(source, target):
        target.append("items", {
            "item_code": source.custom_service_type,
            "item_name": frappe.get_cached_value("Item", source.custom_service_type, "item_name"),
            "uom": frappe.get_cached_value("Item", source.custom_service_type, "purchase_uom")
                or frappe.get_cached_value("Item", source.custom_service_type, "stock_uom"),
            "qty": 1,
            "rate": source.custom_onward_flight_cost_as_per_invoice
        })

    doc = get_mapped_doc(
        "Travel Flight Details",
        source_name,
        {
            "Travel Flight Details": {
                "doctype": "Purchase Invoice",
                "field_map": {
                    "custom_onward_flight_booking_vendor": "supplier",
                    "custom_flight_invoice_id": "bill_no",
                    "custom_flight_invoice_attachment": "custom_supplier_invoice"
                },
            }
        },
        postprocess=get_missing_values,
    )
    return doc

@frappe.whitelist()
def make_purchase_invoice(source_name):
    travel_flight_doc = frappe.get_doc("Travel Flight Details", source_name)

    if travel_flight_doc.custom_journey_type not in ("Round Trip", "Onward & Return Trip"):
        frappe.throw(
            f"Purchase Invoice creation is not supported for journey type "
            f"{travel_flight_doc.custom_journey_type}"
        )

    def set_missing_values(source, target):
        target.supplier = source.custom_flight_booking_vendor

        if source.custom_journey_type == "Round Trip":
            target.bill_no = source.custom_round_trip_invoice_id
            target.custom_supplier_invoice = source.custom_round_trip_invoice_attachment
            rate = source.custom_round_trip_cost_as_per_invoice
        else:  # Onward & Return Trip
            target.bill_no = source.custom_return_flight_invoice_id
            target.custom_supplier_invoice = source.custom_return_flight_invoice_attachment
            rate = source.custom_return_flight_cost_as_per_invoice

        item = frappe.get_cached_doc("Item", source.custom_service_type)

        target.append("items", {
            "item_code": source.custom_service_type,
            "item_name": item.item_name,
            "uom": item.purchase_uom or item.stock_uom,
            "qty": 1,
            "rate": rate,
        })

    doc = get_mapped_doc(
        "Travel Flight Details",
        source_name,
        {
            "Travel Flight Details": {
                "doctype": "Purchase Invoice",
            }
        },
        postprocess=set_missing_values,
    )
    return doc
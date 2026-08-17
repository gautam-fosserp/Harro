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
    travel_flight_doc = frappe.get_doc("Travel Flight Details", source_name)

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

    def get_missing_values(source, target):
        item = frappe.get_cached_doc("Item", source.custom_service_type)
        rate = source.custom_onward_flight_cost_as_per_invoice

        # update item price BEFORE building the item row
        update_item_price(item.name, rate)

        target.append("items", {
            "item_code": source.custom_service_type,
            "item_name": item.item_name,
            "uom": item.purchase_uom or item.stock_uom,
            "stock_uom": item.stock_uom,
            "conversion_factor": 1,
            "qty": 1,
            "rate": rate,
            "price_list_rate": rate,
            "cost_center": "Main - Harro IN",
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
                    "custom_flight_invoice_attachment": "custom_supplier_invoice",
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

        # update item price BEFORE building the item row
        update_item_price(item.name, rate)

        target.append("items", {
            "item_code": source.custom_service_type,
            "item_name": item.item_name,
            "uom": item.purchase_uom or item.stock_uom,
            "stock_uom": item.stock_uom,
            "conversion_factor": 1,
            "qty": 1,
            "rate": rate,
            "price_list_rate": rate,
            "cost_center": "Main - Harro IN",
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


@frappe.whitelist()
def send_cancellation_request_email(source_name):
    doc = frappe.get_doc("Travel Flight Details", source_name)

    # Fetch all users having Travel Manager role
    travel_managers = frappe.get_all(
        "Has Role",
        filters={
            "role": "Travel Manager",
        },
        fields=["parent"],
    )

    recipients = []

    for row in travel_managers:
        user = frappe.db.get_value(
            "User",
            row.parent,
            ["name", "email", "enabled"],
            as_dict=True,
        )

        if user and user.enabled and user.email:
            recipients.append(user.email)

    # Remove duplicate emails while preserving order
    recipients = list(dict.fromkeys(recipients))

    if not recipients:
        frappe.throw(
            "No active users found with the Travel Manager role."
        )

    employee_name = ""

    if doc.employee:
        employee_name = (
            frappe.db.get_value(
                "Employee",
                doc.employee,
                "employee_name",
            )
            or doc.employee
        )

    travel_planning = doc.travel_planning or "-"

    travel_planning_link = frappe.utils.get_url_to_form(
        "Travel Planning",
        doc.travel_planning
    ) if doc.travel_planning else "#"

    flight_details_link = frappe.utils.get_url_to_form(
        "Travel Flight Details",
        doc.name,
    )

    subject = (
        f"Travel Planning {travel_planning} – "
        f"Flight Cancellation Request for {employee_name}"
    )

    message = f"""
    <div style="
        margin:0;
        padding:0;
        background:#f3f6f9;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
        color:#1f2937;
    ">

        <div style="
            width:100%;
            padding:45px 18px;
            box-sizing:border-box;
        ">

            <!-- Main Card -->
            <div style="
                max-width:650px;
                margin:0 auto;
                background:#ffffff;
                border-radius:16px;
                overflow:hidden;
                border:1px solid #e6eaf0;
                box-shadow:0 8px 30px rgba(15,23,42,0.08);
            ">

                <!-- Header -->
                <div style="
                    padding:34px 36px;
                    background:linear-gradient(135deg,#1f4e78 0%,#285f8f 100%);
                ">

                    <div style="
                        margin:0;
                        color:#ffffff;
                        font-size:27px;
                        line-height:36px;
                        font-weight:700;
                        letter-spacing:-0.4px;
                    ">
                        Flight Cancellation Request
                    </div>

                </div>

                <!-- Body -->
                <div style="padding:36px;">

                    <!-- Greeting -->
                    <p style="
                        margin:0 0 22px;
                        font-size:16px;
                        line-height:26px;
                        color:#111827;
                    ">
                        Dear Travel Manager,
                    </p>

                    <!-- Main Message -->
                    <p style="
                        margin:0;
                        font-size:15px;
                        line-height:27px;
                        color:#4b5563;
                    ">
                        This is to inform you that a
                        <strong style="color:#111827;font-weight:700;">
                            flight cancellation request
                        </strong>
                        has been updated for
                        <strong style="color:#111827;font-weight:700;">
                            {frappe.utils.escape_html(employee_name)}
                        </strong>
                        under Travel Planning
                        under Travel Planning
                        <a href="{travel_planning_link}"
                            style="
                                color:#1f4e78;
                                text-decoration:none;
                                font-weight:700;
                            ">
                            {frappe.utils.escape_html(travel_planning or "")}
                        </a>.
                    </p>

                    <!-- Action Message -->
                    <div style="
                        margin:28px 0;
                        padding:20px 22px;
                        background:#f8fafc;
                        border:1px solid #e5eaf0;
                        border-radius:10px;
                    ">

                        <p style="
                            margin:0;
                            font-size:14px;
                            line-height:24px;
                            color:#4b5563;
                        ">
                            Kindly review the cancellation details and proceed
                            with the necessary actions.
                        </p>

                    </div>

                    <!-- CTA Section -->
                    <div style="
                        margin:34px 0 10px;
                        text-align:center;
                    ">

                        <a href="{flight_details_link}"
                        style="
                            display:inline-block;
                            padding:14px 30px;
                            background:#1f4e78;
                            color:#ffffff;
                            text-decoration:none;
                            border-radius:8px;
                            font-size:14px;
                            line-height:20px;
                            font-weight:700;
                            letter-spacing:0.1px;
                            box-shadow:0 4px 10px rgba(31,78,120,0.20);
                        ">
                            View Travel Flight Details
                        </a>

                    </div>

                    <!-- Signature -->
                    <div style="
                        margin-top:36px;
                        padding-top:24px;
                        border-top:1px solid #edf0f3;
                    ">  

                        <p style="
                            margin:0;
                            font-size:14px;
                            line-height:23px;
                            color:#6b7280;
                        ">
                            Regards,<br>
                            <strong style="
                                color:#1f2937;
                                font-weight:600;
                            ">
                                Travel Requestor
                            </strong>
                        </p>

                    </div>

                </div>

                <!-- Footer -->
                <div style="
                    padding:18px 36px;
                    background:#fafbfc;
                    border-top:1px solid #edf0f3;
                    text-align:center;
                ">

                    <p style="
                        margin:0;
                        font-size:11px;
                        line-height:18px;
                        color:#a0a8b3;
                    ">
                        This is an automated notification.
                    </p>

                </div>

            </div>

        </div>

    </div>
"""

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
    )

    frappe.msgprint(
        f"Email notification sent to {len(recipients)} Travel Manager(s)."
    )

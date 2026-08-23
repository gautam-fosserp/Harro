# Copyright (c) 2025, Fosserp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.desk.form.assign_to import add


class TravelPlanning(Document):
    def on_update(self):
        self.send_ticket_booked_emails()
        self.assign_travel_plan_to_employees()

    def assign_travel_plan_to_employees(self):
        if self.is_new():
            return
        
        old_doc = self.get_doc_before_save()
        if not old_doc or old_doc.workflow_state == self.workflow_state:
            return
        if self.workflow_state != "Waiting for Travel Manager to Update Travel Plan":
            return
        
        assigned_users = set()
        for row in self.travel_itinerary:
            if not row.custom_employee:
                continue
            user = frappe.db.get_value(
                "Employee",
                row.custom_employee,
                "user_id"
            )

            if not user:
                continue

            assigned_users.add(user)

        for user in assigned_users:
            if frappe.db.exists(
                "ToDo",
                {
                    "reference_type": self.doctype,
                    "reference_name": self.name,
                    "allocated_to": user,
                    "status": ("!=", "Cancelled"), 
                },
            ):
                continue
            add({
                "assign_to": [user],
                "doctype": self.doctype,
                "name": self.name,
                "description": "Please Update Your Travel Plan."
            })

    def send_ticket_booked_emails(self):
        if self.is_new():
            return
        
        old_doc = self.get_doc_before_save()

        if not old_doc or old_doc.workflow_state == self.workflow_state:
            return
        if self.workflow_state == "Flight Ticket Booked":
            frappe.enqueue(
                method="harro.harro.doctype.travel_planning.travel_planning.send_flight_booking_emails",
                queue="default",
                enqueue_after_commit=True,
                docname=self.name
            )
        elif self.workflow_state == "Hotel Booked":
            frappe.enqueue(
                method="harro.harro.doctype.travel_planning.travel_planning.send_hotel_booking_emails",
                queue="default",
                enqueue_after_commit=True,
                docname=self.name
            )
        elif self.workflow_state == "Flight and Hotel Ticket Booked":
            frappe.enqueue(
                method="harro.harro.doctype.travel_planning.travel_planning.send_combined_segment_emails",
                queue="default",
                enqueue_after_commit=True,
                docname=self.name
            )

def send_combined_segment_emails(docname):
    doc = frappe.get_doc("Travel Planning", docname)

    flight_attachment_fields = [
        "custom_flight_bill",
        "custom_return_flight_ticket"
    ]
    hotel_attachment_fields = ["custom_taxi_bill"]

    flight_rows = frappe.get_all(
        "Travel Flight Details",
        filters={"travel_planning": docname},
        fields=["name", "employee", "travel_itinerary_row", "segment_no", "contact_email",
                "custom_onward_travel_from", "custom_onward_travel_to", "custom_onward_travel_date",
                "custom_return_travel_from", "custom_return_travel_to", "custom_return_travel_date",
                "custom_flight_booking_status"] + flight_attachment_fields,
    )
    hotel_rows = frappe.get_all(
        "Travel Hotel Booking",
        filters={"travel_planning": docname},
        fields=["name", "employee", "travel_itinerary_row", "segment_no", "contact_email",
                "custom_hotel_name", "check_in_date", "check_out_date",
                "custom_hotel_booking_status", "custom_payment_terms_for_hotel_booking"]
               + hotel_attachment_fields
               + ["custom_laundry_facility", "custom_laundry_facility_remarks",
                  "custom_discount_on_meal", "custom_meal_discount_remarks",
                  "custom_airport_transport", "custom_airport_transport_remarks",
                  "custom_break_fast", "custom_break_fast_remarks",
                  "custom_wifi", "custom_wifi_remarks"],
    )
    def group_by_row(rows):
        grouped = {}
        for r in rows:
            grouped.setdefault(r.travel_itinerary_row, {})[r.segment_no] = r
        return grouped

    flights_by_row = group_by_row(flight_rows)
    hotels_by_row = group_by_row(hotel_rows)

    all_rows = set(flights_by_row) | set(hotels_by_row)
    travel_planning_link = f"""<a href="{frappe.utils.get_url_to_form(doc.doctype, doc.name)}">{doc.name}</a>"""

    for itinerary_row in all_rows:
        f_segments = flights_by_row.get(itinerary_row, {})
        h_segments = hotels_by_row.get(itinerary_row, {})
        segment_numbers = sorted(set(f_segments) | set(h_segments))

        for seg_no in segment_numbers:
            flight = f_segments.get(seg_no)
            hotel = h_segments.get(seg_no)

            # Skip if this exact pairing was already emailed
            # if flight and flight.get("custom_booking_confirmation_email_sent"):
            #     flight = flight if not flight.get("custom_booking_confirmation_email_sent") else None
            # already_sent = (
            #     (not flight or frappe.db.get_value("Travel Flight Details", flight.name, "custom_booking_confirmation_email_sent"))
            #     and (not hotel or frappe.db.get_value("Travel Hotel Booking", hotel.name, "custom_booking_confirmation_email_sent"))
            # )
            # if already_sent:
            #     continue

            contact_email = (flight and flight.contact_email) or (hotel and hotel.contact_email)
            if not contact_email:
                continue

            employee = (flight and flight.employee) or (hotel and hotel.employee)
            employee_name = frappe.db.get_value("Employee", employee, "employee_name") or employee

            attachments = []
            flight_block = ""
            if flight:
                attachments += [
                    {"file_url": flight.get(f)} for f in flight_attachment_fields if flight.get(f)
                ]
                flight_block = f"""
                    <b>Flight:</b><br>
                    Onward: {flight.custom_onward_travel_from or '-'} → {flight.custom_onward_travel_to or '-'}
                    ({flight.custom_onward_travel_date or '-'})<br>
                    Return: {flight.custom_return_travel_from or '-'} → {flight.custom_return_travel_to or '-'}
                    ({flight.custom_return_travel_date or '-'})<br>
                    Status: {flight.custom_flight_booking_status or '-'}<br><br>
                """

            hotel_block = ""
            if hotel:
                attachments += [
                    {"file_url": hotel.get(f)} for f in hotel_attachment_fields if hotel.get(f)
                ]
                payment_terms_html = _build_payment_terms_html(hotel)
                preferences_html = _build_preferences_html(hotel)
                hotel_block = f"""
                    <b>Hotel:</b> {hotel.custom_hotel_name or '-'}<br>
                    Check-in: {hotel.check_in_date or '-'} → Check-out: {hotel.check_out_date or '-'}<br>
                    Status: {hotel.custom_hotel_booking_status or '-'}<br><br>
                    {payment_terms_html}
                    {preferences_html}
                """

            frappe.sendmail(
                recipients=[contact_email],
                subject=f"{doc.name}: Flight & Hotel Booking Confirmation for {employee_name} (Segment {seg_no})",
                message=f"""
                    Hello {employee_name},<br><br>

                    Your flight and hotel booking for segment {seg_no} has been confirmed.
                    Please find the attachments below.<br><br>

                    <b>Travel Planning:</b> {travel_planning_link}<br>
                    <b>Employee:</b> {employee_name}<br><br>

                    {flight_block}
                    {hotel_block}

                    Regards,<br>
                    <b>Travel Team</b>
                """,
                attachments=attachments,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
            )

            # if flight:
            #     frappe.db.set_value("Travel Flight Details", flight.name, "custom_booking_confirmation_email_sent", 1)
            # if hotel:
            #     frappe.db.set_value("Travel Hotel Booking", hotel.name, "custom_booking_confirmation_email_sent", 1)

def send_flight_booking_emails(docname):
    doc = frappe.get_doc("Travel Planning", docname)
    # Additional flight segments (Travel Flight Details) — one email per segment,
    # mirroring the primary itinerary row's email.
    segment_attachment_fields = [
        "custom_flight_bill",
        "custom_return_flight_ticket",
        "custom_flight_invoice_attachment",
        "custom_return_flight_invoice_attachment",
    ]
    for segment in frappe.get_all(
        "Travel Flight Details",
        filters={"travel_planning": docname},
        fields=["name", "employee", "contact_email"] + segment_attachment_fields,
    ):
        if not segment.contact_email:
            continue

        employee_name = frappe.db.get_value("Employee", segment.employee, "employee_name") or segment.employee
        attachments = [
            {"file_url": segment.get(field)}
            for field in segment_attachment_fields
            if segment.get(field)
        ]
        travel_planning_link = f"""<a href="{frappe.utils.get_url_to_form(doc.doctype, doc.name)}">{doc.name}</a>"""

        frappe.sendmail(
            recipients=[segment.contact_email],
            subject=f"{doc.name}: Ticket has been booked for {employee_name}",
            message=f"""
                Hello {employee_name},<br><br>

                Your flight ticket has been booked.
                Please find the ticket attachments below.<br><br>

                <b>Travel Planning:</b> {travel_planning_link}<br>
                <b>Employee:</b> {employee_name}<br><br>

                Regards,<br>
                <b>Travel Team</b>
            """,
            attachments=attachments,
            reference_doctype=doc.doctype,
            reference_name=doc.name
        )


def send_hotel_booking_emails(docname):
    doc = frappe.get_doc("Travel Planning", docname)

    hotel_attachment_fields = [
        "custom_taxi_bill",
    ]
    travel_planning_link = f"""<a href="{frappe.utils.get_url_to_form(doc.doctype, doc.name)}">{doc.name}</a>"""

    requestor_name = frappe.db.get_value("Employee", doc.travel_requestor, "employee_name")

    for row in doc.travel_itinerary:
        # skip rows that already got this email
        if row.get("hotel_booking_email_sent"):
            continue

        if not row.get("custom_contact_email"):
            continue

        attachments = [
            {"file_url": row.get(field)}
            for field in hotel_attachment_fields
            if row.get(field)
        ]

        # Build travel preferences block (only if the field exists on the row)
        preferences_html = _build_preferences_html(row)
        payment_terms_html = _build_payment_terms_html(row)

        # ── Email to Employee
        if row.custom_contact_email:
            frappe.sendmail(
                recipients=[row.custom_contact_email],
                subject=f"{doc.name}: Hotel has been booked for {row.employee_name}",
                message=f"""
                    Hello {row.employee_name},<br><br>

                    Your hotel has been booked.
                    Please find the hotel voucher attachments below.<br><br>

                    <b>Travel Planning:</b> {travel_planning_link}<br>
                    <b>Employee:</b> {row.employee_name}<br><br>

                    {payment_terms_html}

                    {preferences_html}

                    Regards,<br>
                    <b>Travel Team</b>
                """,
                attachments=attachments,
                reference_doctype=doc.doctype,
                reference_name=doc.name
            )
            
            row.db_set("hotel_booking_email_sent", 1)

        # ── Email to Requestor 
        # if doc.custom_requestor_contact_email:
        #     frappe.sendmail(
        #         recipients=[doc.custom_requestor_contact_email],
        #         subject=f"Hotel has been booked for {row.employee_name} against Travel Request {row.travel_request}",
        #         message=f"""
        #             Hello {requestor_name},<br><br>

        #             This is to inform you that the hotel booking has been confirmed for {row.employee_name}
        #             against Travel Request {row.travel_request}. Please find the hotel voucher attached
        #             for your reference.<br><br>

        #             <b>Travel Planning:</b> {doc.name}<br>
        #             <b>Employee:</b> {row.employee_name}<br><br>

        #             {preferences_html}

        #             Regards,<br>
        #             <b>Travel Team</b>
        #         """,
        #         attachments=attachments,
        #         reference_doctype=doc.doctype,
        #         reference_name=doc.name
        #     )

    # Additional hotel segments (Travel Hotel Booking) — one email per segment,
    # mirroring the primary itinerary row's email above.
    segment_preference_fields = [
        "custom_laundry_facility", "custom_laundry_facility_remarks",
        "custom_discount_on_meal", "custom_meal_discount_remarks",
        "custom_airport_transport", "custom_airport_transport_remarks",
        "custom_break_fast", "custom_break_fast_remarks",
        "custom_wifi", "custom_wifi_remarks",
    ]
    for segment in frappe.get_all(
        "Travel Hotel Booking",
        filters={"travel_planning": docname},
        fields=["name", "employee", "contact_email", "custom_taxi_bill",
                "custom_payment_terms_for_hotel_booking"] + segment_preference_fields,
    ):
        if not segment.contact_email:
            continue

        employee_name = frappe.db.get_value("Employee", segment.employee, "employee_name") or segment.employee
        attachments = [{"file_url": segment.custom_taxi_bill}] if segment.custom_taxi_bill else []
        segment_preferences_html = _build_preferences_html(segment)
        segment_payment_terms_html = _build_payment_terms_html(segment)

        frappe.sendmail(
            recipients=[segment.contact_email],
            subject=f"{doc.name}: Hotel has been booked for {employee_name}",
            message=f"""
                Hello {employee_name},<br><br>

                Your hotel has been booked.
                Please find the hotel voucher attachments below.<br><br>

                <b>Travel Planning:</b> {travel_planning_link}<br>
                <b>Employee:</b> {employee_name}<br><br>

                {segment_payment_terms_html}

                {segment_preferences_html}

                Regards,<br>
                <b>Travel Team</b>
            """,
            attachments=attachments,
            reference_doctype=doc.doctype,
            reference_name=doc.name
        )


def _build_payment_terms_html(row):
    payment_terms = row.get("custom_payment_terms_for_hotel_booking")
    if not payment_terms:
        return ""
    return f"<b>Payment Terms for Hotel Booking:</b> {payment_terms}<br><br>"


def _build_preferences_html(row):
    preferences = []

    preference_field_map = {
        "custom_laundry_facility":  ("Laundry Facility",     "custom_laundry_facility_remarks"),
        "custom_discount_on_meal":  ("Discount on Meals",    "custom_meal_discount_remarks"),
        "custom_airport_transport": ("Airport Transport",    "custom_airport_transport_remarks"),
        "custom_break_fast":        ("Breakfast",            "custom_break_fast_remarks"),
        "custom_wifi":              ("Wi-Fi",                "custom_wifi_remarks"),
    }

    for field, (label, remarks_field) in preference_field_map.items():
        value = row.get(field)
        if not value:
            continue

        remarks = row.get(remarks_field, "")
        if isinstance(value, str) and value.strip():
            # String field — show value inline
            display = f"{label} – {value}"
        elif remarks:
            # Checkbox with a remarks field
            display = f"{label} – {remarks}"
        else:
            # Checkbox with no remarks
            display = label

        preferences.append(f"<li>{display}</li>")

    if not preferences:
        return ""

    items = "\n".join(preferences)
    return f"""
        <b>Travel Preferences:</b><br>
        <ul style="margin-top:4px;">
            {items}
        </ul><br>
    """


@frappe.whitelist()
def create_purchase_invoice(source_name, target_doc=None):
	doclist = get_mapped_doc(
		"Travel Planning",
		source_name,
		{
			"Travel Planning": {
				"doctype": "Purchase Invoice", 
				"field_map" : {
					"name" : "travel_planning"
				}
			},
		},
		target_doc,
	)

	return doclist

@frappe.whitelist()
def get_travel_dates(travel_request):
    items = frappe.get_all(
        "Travel Itinerary",
        filters={"parent": travel_request},
        fields=["custom_onward_travel_date","custom_return_travel_date"],
        limit=1
    )

    if not items:
        return {}
    
    return items[0]

@frappe.whitelist()
def create_travel_checklist(source_name):
    tp = frappe.get_doc("Travel Planning", source_name)

    created = []
    skipped = []

    for row in tp.travel_itinerary:
        if not row.travel_request:
            continue

        # Check if Travel Checklist exists
        tc_name = frappe.db.get_value(
            "Travel Checklist",
            {"custom_travel_request": row.travel_request},
            "name"
        )

        if tc_name:
            # Generate link to existing Travel Checklist
            skipped.append(f'<a href="/app/travel-checklist/{tc_name}" target="_blank">{row.travel_request}</a>')
            continue

        # Create new Travel Checklist
        tc = frappe.new_doc("Travel Checklist")
        tc.custom_travel_request = row.travel_request
        tc.travel_type = tp.travel_type
        tc.travell_to = row.travel_to
        tc.visit_no = 0
        tc.insert(ignore_permissions=True)

        # Add link for newly created checklist
        created.append(f'<a href="/app/travel-checklist/{tc.name}" target="_blank">{row.travel_request}</a>')

    # Build message with links
    message = ""
    if created:
        message += f"Created Travel Checklist for: {', '.join(created)}<br>"
    if skipped:
        message += f"⚠ Already exists for: {', '.join(skipped)}"

    return message


@frappe.whitelist()
def get_flight_purchase_invoice_defaults(employee_row, travel_doc):
    import json

    if isinstance(employee_row, str):
        employee_row = json.loads(employee_row)

    row = frappe._dict(employee_row)

    ba_number = frappe.get_value("Travel Planning", travel_doc, "ba_number")

    mandatory_fields = {
        "Vendor Name": row.get("custom_flight_booking_vendor"),
        "Bill No": row.get("custom_flight_invoice_id"),
        "BA Number": ba_number,
        "Service Type": row.get("custom_service_type"),
        "Total Amount": row.get("custom_total_flight_cost_as_per_invoice")
    }

    missing_fields = [field for field, value in mandatory_fields.items() if not value]

    if missing_fields:
        frappe.throw(f"Mandatory field(s) missing: {', '.join(missing_fields)}")

    doc = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": row.custom_flight_booking_vendor,
        "travel_planning": travel_doc,
        "bill_no": row.custom_flight_invoice_id,
        "project": ba_number,
        "custom_supplier_invoice": row.get("custom_flight_invoice_attachment")
    })

    doc.append("items", {
        "item_code": row.custom_service_type,
        "qty": 1,
        "rate": row.custom_total_flight_cost_as_per_invoice
    })

    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True

    doc.insert()

    attachments = [
        row.get("custom_flight_invoice_attachment"),
        row.get("custom_onward_flight_invoice_attachment"),
        row.get("custom_return_flight_invoice_attachment")
    ]

    for file_url in attachments:
        if file_url:
            frappe.get_doc({
                "doctype": "File",
                "file_url": file_url,
                "attached_to_doctype": "Purchase Invoice",
                "attached_to_name": doc.name
            }).insert(ignore_permissions=True)

    return doc.name


@frappe.whitelist()
def custom_flight_email_sent(expense_detail_row, travel_planning):
    row = frappe.parse_json(expense_detail_row)

    child = frappe.get_doc("Travel Planning Employee Details", row.get("name"))

    if child.custom_flight_email_sent:
        frappe.throw("Email already sent for this row.")

    accounts_managers = frappe.get_all(
        "Has Role",
        filters={"role": "Accounts Manager"},
        pluck="parent"
    )

    recipients = frappe.get_all(
        "User",
        filters={
            "name": ["in", accounts_managers],
            "enabled": 1
        },
        pluck="email"
    )

    if not recipients:
        frappe.throw("No active Accounts Manager found")

    subject = "Action Required: Supplier Invoice Details Updated – Please Create Purchase Invoice"
    doc_link = frappe.utils.get_url_to_form("Travel Planning", travel_planning)

    message = f"""
    <p>Dear Accounts Manager,</p>

    <p>
    The flight invoice details have been updated against the travel request 
    (<b>{child.travel_request}</b>). Kindly review and proceed with the creation 
    of the Purchase Invoice and payment processing.
    </p>

    <p>
    <a href="{doc_link}">Open Travel Planning</a>
    </p>

    <p>
    Regards,<br>
    Travel Manager
    </p>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message
    )

    child.db_set("custom_flight_email_sent", 1)

    return "Email sent successfully"


@frappe.whitelist()
def get_hotel_purchase_invoice_defaults(employee_row, travel_doc):
    import json

    if isinstance(employee_row, str):
        employee_row = json.loads(employee_row)

    row = frappe._dict(employee_row)

    ba_number = frappe.get_value("Travel Planning", travel_doc, "ba_number")

    mandatory_fields = {
        "Vendor Name": row.get("custom_hotel_booking_vendor_name"),
        "Bill No": row.get("custom_hotel_invoice_id"),
        "BA Number": ba_number,
		"Service Type": row.get("custom_service_category"),
		"Total Amount": row.get("custom_total_hotel_charge")
    }

    missing_fields = [field for field, value in mandatory_fields.items() if not value]

    if missing_fields:
        frappe.throw(f"Mandatory field(s) missing: {', '.join(missing_fields)}")

    doc = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": row.custom_hotel_booking_vendor_name,
        "travel_planning": travel_doc,
        "bill_no": row.custom_hotel_invoice_id,
        "project": ba_number,
		"custom_supplier_invoice": row.custom_taxi_bill
    })

    doc.append(
        "items",
        {
            "item_code": row.custom_service_category,
            "qty": 1,
            "rate": row.custom_total_hotel_charge
        }
    )

    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True

    doc.insert()

    return doc.name


@frappe.whitelist()
def custom_send_email_hotel(expense_detail_row, travel_planning):
    row = frappe.parse_json(expense_detail_row)

    child = frappe.get_doc("Travel Planning Employee Details", row.get("name"))

    if child.custom_hotel_email_sent:
        frappe.throw("Email already sent for this row.")

    accounts_managers = frappe.get_all(
        "Has Role",
        filters={"role": "Accounts Manager"},
        pluck="parent"
    )

    recipients = frappe.get_all(
        "User",
        filters={
            "name": ["in", accounts_managers],
            "enabled": 1
        },
        pluck="email"
    )

    if not recipients:
        frappe.throw("No active Accounts Manager found")

    subject = "Action Required: Supplier Invoice Details Updated – Please Create Purchase Invoice"
    doc_link = frappe.utils.get_url_to_form("Travel Planning", travel_planning)

    message = f"""
    <p>Dear Accounts Manager,</p>

    <p>
    The Hotel invoice details have been updated against the travel request 
    (<b>{child.travel_request}</b>). Kindly review and proceed with the creation 
    of the Purchase Invoice and payment processing.
    </p>

    <p>
    <a href="{doc_link}">Open Travel Planning</a>
    </p>

    <p>
    Regards,<br>
    Travel Manager
    </p>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message
    )

    child.db_set("custom_hotel_email_sent", 1)

    return "Email sent successfully"

@frappe.whitelist()
def get_taxi_purchase_invoice_defaults(employee_row, travel_doc):
    import json

    if isinstance(employee_row, str):
        employee_row = json.loads(employee_row)

    row = frappe._dict(employee_row)

    ba_number = frappe.get_value("Travel Planning", travel_doc, "ba_number")

    mandatory_fields = {
        "Vendor Name": row.get("custom_taxi_vendor"),
        "Bill No": row.get("custom_taxi_invoice_id"),
        "BA Number": ba_number,
		"Service Type": row.get("custom_taxi_type"),
		"Total Amount": row.get("taxi_coast")
    }

    missing_fields = [field for field, value in mandatory_fields.items() if not value]

    if missing_fields:
        frappe.throw(f"Mandatory field(s) missing: {', '.join(missing_fields)}")

    doc = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": row.custom_taxi_vendor,
        "travel_planning": travel_doc,
        "bill_no": row.custom_taxi_invoice_id,
        "project": ba_number,
		"custom_supplier_invoice": row.custom_taxi_invoice_attachment
    })

    doc.append(
        "items",
        {
            "item_code": row.custom_service_item,
            "qty": 1,
            "rate": row.taxi_coast
        }
    )

    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True

    doc.insert()

    return doc.name


@frappe.whitelist()
def custom_send_email(expense_detail_row, travel_planning):
    row = frappe.parse_json(expense_detail_row)

    child = frappe.get_doc("Travel Planning Employee Details", row.get("name"))

    if child.custom_email_sent:
        frappe.throw("Email already sent for this row.")

    accounts_managers = frappe.get_all(
        "Has Role",
        filters={"role": "Accounts Manager"},
        pluck="parent"
    )

    recipients = frappe.get_all(
        "User",
        filters={
            "name": ["in", accounts_managers],
            "enabled": 1
        },
        pluck="email"
    )

    if not recipients:
        frappe.throw("No active Accounts Manager found")

    subject = "Action Required: Supplier Invoice Details Updated – Please Create Purchase Invoice"
    doc_link = frappe.utils.get_url_to_form("Travel Planning", travel_planning)

    message = f"""
    <p>Dear Accounts Manager,</p>

    <p>
    The taxi invoice details have been updated against the travel request 
    (<b>{child.travel_request}</b>). Kindly review and proceed with the creation of the Purchase Invoice and payment processing.
    </p>

    <p>
    <a href="{doc_link}">Open Travel Planning</a>
    </p>

    <p>
    Regards,<br>
    Travel Manager
    </p>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message
    )

    child.db_set("custom_email_sent", 1)

    return "Email sent successfully"



@frappe.whitelist()
def send_revised_ticket_email(travel_planning_name, itinerary_row_name):

    # ── Load parent Travel Planning 
    tp = frappe.get_doc("Travel Planning", travel_planning_name)

    # ── Find the specific child row
    itinerary_row = None
    for row in tp.travel_itinerary:
        if row.name == itinerary_row_name:
            itinerary_row = row
            break

    if not itinerary_row:
        frappe.throw(f"Row {itinerary_row_name} not found in {travel_planning_name}")

    # Validation
    if not itinerary_row.custom_rescheduled_flight_ticket:
        frappe.throw("Please attach the Rescheduled Flight Ticket before sending.")

    if not itinerary_row.custom_contact_email:
        frappe.throw("Employee Contact Email is missing in this row.")

    if not tp.custom_requestor_contact_email:
        frappe.throw("Requestor Contact Email is missing in Travel Planning.")

    # Helper: resolve a file URL → attachment dict
    def resolve_attachment(file_url):
        if not file_url:
            return None
        file_doc = frappe.get_all(
            "File",
            filters={"file_url": file_url},
            fields=["name", "file_name"],
            limit=1
        )
        if file_doc:
            return {
                "fname": file_doc[0]["file_name"],
                "fid": file_doc[0]["name"],
            }
        else:
            try:
                file_content = frappe.get_file(file_url)
                return {
                    "fname": file_url.split("/")[-1],
                    "fcontent": file_content,
                }
            except Exception:
                frappe.log_error(f"Could not read file: {file_url}", "Send Revised Ticket")
                return None

    # Resolve both attachments
    attachments = []

    flight_attachment = resolve_attachment(itinerary_row.custom_rescheduled_flight_ticket)
    if flight_attachment:
        attachments.append(flight_attachment)

    hotel_attachment = resolve_attachment(itinerary_row.custom_rescheduled_hotel_ticket_)
    if hotel_attachment:
        attachments.append(hotel_attachment)

    # Get data for email content
    employee_name = itinerary_row.employee_name or ""
    travel_request_id = itinerary_row.travel_request or ""

    requestor_name = ""
    if tp.travel_requestor:
        requestor_name = frappe.db.get_value(
            "Employee", tp.travel_requestor, "employee_name"
        ) or tp.custom_requestor_contact_email

    # EMAIL 1 — To Employee
    employee_message = f"""
    <p>Hello {employee_name},</p>

    <p>This is to inform you that your ticket against
    <b>Travel Request ID {travel_request_id}</b> has been rescheduled.</p>

    <p>Please find the rescheduled ticket attached below for your reference.</p>

    <p>For any queries regarding the change, please contact the Travel Team.</p>

    <p>Thank you!</p>

    <p>Regards,<br>Travel Team</p>
    """

    frappe.sendmail(
        recipients=[itinerary_row.custom_contact_email],
        subject="Ticket Has Been Rescheduled",
        message=employee_message,
        attachments=attachments,
        reference_doctype="Travel Planning",
        reference_name=travel_planning_name,
    )

    # EMAIL 2 — To Requestor
    requestor_message = f"""
    <p>Hello {requestor_name},</p>

    <p>This is to inform you that the ticket has been rescheduled for
    <b>{employee_name}</b> against Travel Request <b>{travel_request_id}</b>.</p>

    <p>Please find the documents attached for your reference.</p>

    <p><b>Travel Planning:</b> {travel_planning_name}<br>
    <b>Employee:</b> {employee_name}</p>

    <p>Regards,<br>Travel Team</p>
    """

    frappe.sendmail(
        recipients=[tp.custom_requestor_contact_email],
        subject="Ticket Has Been Rescheduled",
        message=requestor_message,
        attachments=attachments,
        reference_doctype="Travel Planning",
        reference_name=travel_planning_name,
    )

    return "Emails sent successfully."


@frappe.whitelist()
def make_expense_claim(source_name, target_doc=None):
    doc = frappe.get_doc("Travel Planning", source_name)

    expense_claim = frappe.new_doc("Expense Claim")
    expense_claim.custom_travel_planning = doc.name

    employee_id = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user},
        "name"
    )

    if employee_id:
        expense_claim.employee = employee_id

    return expense_claim



@frappe.whitelist()
def make_timesheet(source_name, target_doc=None):
    doc = frappe.get_doc("Travel Planning", source_name)

    timesheet = frappe.new_doc("Timesheet")
    timesheet.custom_travel_planning = doc.name
    timesheet.parent_project = doc.ba_number

    return timesheet

import frappe
from frappe.utils import today

@frappe.whitelist()
def make_employee_advance(source_name, target_doc=None):
    travel = frappe.get_doc("Travel Planning", source_name)

    employee_advance = frappe.new_doc("Employee Advance")

    if travel.travel_itinerary:
        row = travel.travel_itinerary[0]

        employee_advance.employee = row.custom_employee
        employee_advance.employee_name = row.employee_name

    employee_advance.posting_date = today()
    employee_advance.custom_employee_advance_type = "Travel Allowance"
    employee_advance.custom_country = travel.custom_country
    employee_advance.custom_travel_planning = travel.name

    return employee_advance

@frappe.whitelist()
def get_flight_segments(travel_planning):
    frappe.has_permission("Travel Flight Details", "read", throw=True)
    return frappe.get_all(
        "Travel Flight Details",
        filters={"travel_planning": travel_planning},
        fields=[
            "name",
            "employee",
            "employee.employee_name as employee_name",
            "travel_itinerary_row",
            "segment_no",
            "custom_onward_travel_date",
            "custom_return_travel_date",
            "custom_return_travel_from",
            "custom_return_travel_to",
            "custom_flight_booking_status",
            "custom_total_flight_cost_as_per_invoice",
            "custom_onward_travel_from",
            "custom_onward_travel_to"
        ],
        order_by="employee, segment_no",
    )


@frappe.whitelist()
def get_hotel_segments(travel_planning):
    frappe.has_permission("Travel Hotel Booking", "read", throw=True)
    return frappe.get_all(
        "Travel Hotel Booking",
        filters={"travel_planning": travel_planning},
        fields=[
            "name",
            "employee",
            "employee.employee_name as employee_name",
            "travel_itinerary_row",
            "segment_no",
            "custom_hotel_name",
            "check_in_date",
            "check_out_date",
            "room_night",
            "custom_stay_required",
            "custom_hotel_booking_status",
            "custom_total_hotel_charge_as_per_invoice",
        ],
        order_by="employee, segment_no",
    )


@frappe.whitelist()
def get_taxi_segments(travel_planning):
    frappe.has_permission("Travel Taxi Details", "read", throw=True)
    return frappe.get_all(
        "Travel Taxi Details",
        filters={"travel_planning": travel_planning},
        fields=[
            "name",
            "employee",
            "employee.employee_name as employee_name",
            "travel_itinerary_row",
            "segment_no",
            "custom_taxi_type",
            "custom_driver_name",
            "custom_taxi_vendor",
            "custom_taxi_required",
            "custom_airport_transfer",
            "custom_daily_transfer",
            "custom_out_of_india",
            "taxi_coast",
        ],
        order_by="employee, segment_no",
    )


@frappe.whitelist()
def delete_travel_segment(doctype, name):
    if doctype not in ("Travel Flight Details", "Travel Hotel Booking", "Travel Taxi Details"):
        frappe.throw(frappe._("Invalid segment doctype"))

    frappe.has_permission(doctype, "delete", throw=True)
    frappe.delete_doc(doctype, name, ignore_permissions=False)


def _throw_if_missing(mandatory_fields, doctype, name):
    missing_fields = [field for field, value in mandatory_fields.items() if not value]
    if missing_fields:
        doc_link = frappe.utils.get_link_to_form(doctype, name)
        field_list = "".join(f"<li>{frappe.utils.escape_html(field)}</li>" for field in missing_fields)
        frappe.throw(
            f"Please fill in the following field(s) on {doc_link} and save before creating a Purchase Invoice:"
            f"<ul>{field_list}</ul>",
            title="Missing Information",
        )


def _get_accounts_manager_emails():
    accounts_managers = frappe.get_all("Has Role", filters={"role": "Accounts Manager"}, pluck="parent")
    recipients = frappe.get_all(
        "User", filters={"name": ["in", accounts_managers], "enabled": 1}, pluck="email"
    )
    if not recipients:
        frappe.throw("No active Accounts Manager found")
    return recipients


def _send_segment_email(travel_planning, segment_label, employee_name):
    recipients = _get_accounts_manager_emails()
    subject = "Action Required: Supplier Invoice Details Updated – Please Create Purchase Invoice"
    doc_link = frappe.utils.get_url_to_form("Travel Planning", travel_planning)

    message = f"""
    <p>Dear Accounts Manager,</p>

    <p>
    The {segment_label} invoice details have been updated for <b>{employee_name}</b>
    on Travel Planning <b>{travel_planning}</b>. Kindly review and proceed with the creation
    of the Purchase Invoice and payment processing.
    </p>

    <p>
    <a href="{doc_link}">Open Travel Planning</a>
    </p>

    <p>
    Regards,<br>
    Travel Manager
    </p>
    """

    frappe.sendmail(recipients=recipients, subject=subject, message=message)


@frappe.whitelist()
def get_flight_segment_purchase_invoice_defaults(name):
    row = frappe.get_doc("Travel Flight Details", name)
    ba_number = frappe.get_value("Travel Planning", row.travel_planning, "ba_number")

    mandatory_fields = {
        "Flight Booking Vendor": row.custom_flight_booking_vendor,
        "Flight Invoice ID": row.custom_flight_invoice_id,
        "BA Number (on Travel Planning)": ba_number,
        "Service Type": row.custom_service_type,
        "Total Flight Cost (As per Invoice)": row.custom_total_flight_cost_as_per_invoice,
    }
    _throw_if_missing(mandatory_fields, "Travel Flight Details", name)

    doc = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": row.custom_flight_booking_vendor,
        "travel_planning": row.travel_planning,
        "bill_no": row.custom_flight_invoice_id,
        "project": ba_number,
        "custom_supplier_invoice": row.custom_flight_invoice_attachment,
    })
    doc.append("items", {
        "item_code": row.custom_service_type,
        "qty": 1,
        "rate": row.custom_total_flight_cost_as_per_invoice,
    })
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True
    doc.insert()

    for file_url in (row.custom_flight_invoice_attachment, row.custom_return_flight_invoice_attachment):
        if file_url:
            frappe.get_doc({
                "doctype": "File",
                "file_url": file_url,
                "attached_to_doctype": "Purchase Invoice",
                "attached_to_name": doc.name,
            }).insert(ignore_permissions=True)

    return doc.name


@frappe.whitelist()
def send_flight_segment_email(name):
    row = frappe.get_doc("Travel Flight Details", name)
    if row.custom_flight_email_sent:
        frappe.throw("Email already sent for this record.")

    employee_name = frappe.get_value("Employee", row.employee, "employee_name") or row.employee
    _send_segment_email(row.travel_planning, "flight", employee_name)
    row.db_set("custom_flight_email_sent", 1)
    return "Email sent successfully"


@frappe.whitelist()
def get_hotel_segment_purchase_invoice_defaults(name):
    row = frappe.get_doc("Travel Hotel Booking", name)
    ba_number = frappe.get_value("Travel Planning", row.travel_planning, "ba_number")

    mandatory_fields = {
        "Hotel Booking Vendor": row.custom_hotel_booking_vendor_name,
        "Hotel Invoice ID": row.custom_hotel_invoice_id,
        "BA Number (on Travel Planning)": ba_number,
        "Service Category": row.custom_service_category,
        "Total Hotel Charge": row.custom_total_hotel_charge,
    }
    _throw_if_missing(mandatory_fields, "Travel Hotel Booking", name)

    doc = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": row.custom_hotel_booking_vendor_name,
        "travel_planning": row.travel_planning,
        "bill_no": row.custom_hotel_invoice_id,
        "project": ba_number,
        "custom_supplier_invoice": row.custom_taxi_bill,
    })
    doc.append("items", {
        "item_code": row.custom_service_category,
        "qty": 1,
        "rate": row.custom_total_hotel_charge,
    })
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True
    doc.insert()

    return doc.name


@frappe.whitelist()
def send_hotel_segment_email(name):
    row = frappe.get_doc("Travel Hotel Booking", name)
    if row.custom_hotel_email_sent:
        frappe.throw("Email already sent for this record.")

    employee_name = frappe.get_value("Employee", row.employee, "employee_name") or row.employee
    _send_segment_email(row.travel_planning, "hotel", employee_name)
    row.db_set("custom_hotel_email_sent", 1)
    return "Email sent successfully"


@frappe.whitelist()
def get_taxi_segment_purchase_invoice_defaults(name):
    row = frappe.get_doc("Travel Taxi Details", name)
    ba_number = frappe.get_value("Travel Planning", row.travel_planning, "ba_number")

    mandatory_fields = {
        "Taxi Vendor": row.custom_taxi_vendor,
        "Taxi Invoice ID": row.custom_taxi_invoice_id,
        "BA Number (on Travel Planning)": ba_number,
        "Taxi Type": row.custom_taxi_type,
        "Taxi Coast": row.taxi_coast,
    }
    _throw_if_missing(mandatory_fields, "Travel Taxi Details", name)

    doc = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": row.custom_taxi_vendor,
        "travel_planning": row.travel_planning,
        "bill_no": row.custom_taxi_invoice_id,
        "project": ba_number,
        "custom_supplier_invoice": row.custom_taxi_invoice_attachment,
    })
    doc.append("items", {
        "item_code": row.custom_service_item,
        "qty": 1,
        "rate": row.taxi_coast,
    })
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True
    doc.insert()

    return doc.name


@frappe.whitelist()
def send_taxi_segment_email(name):
    row = frappe.get_doc("Travel Taxi Details", name)
    if row.custom_taxi_email_sent:
        frappe.throw("Email already sent for this record.")

    employee_name = frappe.get_value("Employee", row.employee, "employee_name") or row.employee
    _send_segment_email(row.travel_planning, "taxi", employee_name)
    row.db_set("custom_taxi_email_sent", 1)
    return "Email sent successfully"


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_travel_managers(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""
        SELECT e.name, e.employee_name
        FROM `tabEmployee` e
        INNER JOIN `tabUser` u ON u.name = e.user_id
        INNER JOIN `tabHas Role` hr ON hr.parent = u.name
        WHERE hr.role = 'Travel Manager'
        AND e.status = 'Active'
        AND (e.name LIKE %(txt)s OR e.employee_name LIKE %(txt)s)
        ORDER BY e.employee_name
        LIMIT %(start)s, %(page_len)s
    """, {
        "txt": "%{0}%".format(txt),
        "start": start,
        "page_len": page_len
    })

@frappe.whitelist()
def send_documents(docname, itinerary_row=None):
    doc = frappe.get_doc("Travel Planning", docname)

    flight_attachment_fields = [
        "custom_evisa",
        "custom_travel_insurance",
        "custom_attach1",
        "custom_attachment1"
    ]

    rows = [r for r in doc.travel_itinerary if not itinerary_row or r.name == itinerary_row]

    for row in rows:
        # skip rows that already got this email
        if row.get("flight_booking_email_sent"):
            frappe.msgprint(f"Email already sent for {row.employee_name or row.name}")
            continue

        if not row.custom_contact_email:
            frappe.msgprint(f"No contact email set for {row.employee_name or row.name}")
            continue

        attachments = [
            {"file_url": row.get(field)}
            for field in flight_attachment_fields
            if row.get(field)
        ]

        attachment_count = len(attachments)
        attachment_label = "document" if attachment_count == 1 else "documents"

        ir_activation_block = ""
        if row.get("custom_ir_activation_done"):
            ir_activation_block = """
                    <div style="background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 16px 20px; margin: 0 0 24px 0;">
                        <p style="margin: 0; color: #065f46; font-size: 14px; font-weight: 500;">
                            Please note that your IR activation has been completed.
                        </p>
                    </div>
            """


        # ── Email to Employee
        message = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f4f5f7; padding: 24px;">
            <div style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">

                <!-- Header -->
                <div style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); padding: 32px 32px 28px 32px; text-align: center;">
                    <div style="font-size: 32px; margin-bottom: 8px;">✈️</div>
                    <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 600;">
                        Your Travel Documents Are Ready
                    </h1>
                </div>

                <!-- Body -->
                <div style="padding: 32px;">
                    <p style="margin: 0 0 16px 0; color: #1f2937; font-size: 15px; line-height: 1.6;">
                        Dear <strong>{row.employee_name}</strong>,
                    </p>

                    <p style="margin: 0 0 20px 0; color: #4b5563; font-size: 15px; line-height: 1.6;">
                        Please find attached your travel documents for your upcoming trip.
                    </p>

                    <!-- Attachment summary card -->
                    <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 16px 20px; margin: 0 0 24px 0;">
                        <p style="margin: 0; color: #1e40af; font-size: 14px; font-weight: 500;">
                            📎 {attachment_count} {attachment_label} attached
                        </p>
                    </div>
                    {ir_activation_block}
                    <p style="margin: 0 0 24px 0; color: #4b5563; font-size: 15px; line-height: 1.6;">
                        Kindly review the attachments and let us know if you require any further assistance.
                    </p>

                    <p style="margin: 0; color: #1f2937; font-size: 15px; line-height: 1.6;">
                        Best Regards,<br>
                        <strong>Travel Team</strong>
                    </p>
                </div>

                <!-- Footer -->
                <div style="background-color: #f9fafb; padding: 20px 32px; border-top: 1px solid #e5e7eb; text-align: center;">
                    <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                        This is an automated message regarding travel plan <strong>{doc.name}</strong>.
                    </p>
                </div>

            </div>
        </div>
        """

        frappe.sendmail(
            recipients=[row.custom_contact_email],
            subject=f"{doc.name}: Travel Documents for your upcoming trip",
            message=message,
            attachments=attachments,
            reference_doctype=doc.doctype,
            reference_name=doc.name
        )

        row.db_set("flight_booking_email_sent", 1)



@frappe.whitelist()
def mark_visa_utilized(employee, country, travel_planning):
    emp = frappe.get_doc("Employee", employee)

    for row in emp.custom_visa_details:
        if (row.visa_country or "").strip().lower() == (country or "").strip().lower():
            if not row.custom_visa_utilized:
                row.db_set("custom_visa_utilized", 1, update_modified=False)
                row.db_set("custom_travel_planning", travel_planning, update_modified=False)
            return {"updated": True, "travel_planning": row.custom_travel_planning}
    return {"updated": False}
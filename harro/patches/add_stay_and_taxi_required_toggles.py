import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

HOTEL_DOCTYPE = "Travel Hotel Booking"
HOTEL_CHECKBOX = "custom_stay_required"
HOTEL_GATED_FIELDS = [
    "preferred_area_for_lodging",
    "check_in_date",
    "check_out_date",
    "room_night",
    "hotel_coast",
    "custom_hotel_name",
    "custom_taxi_bill",
    "custom_hotel_booking_status",
    "custom_hotel_booked_by",
    "custom_hotel_cancellation_details",
    "custom_hotel_cancellation_charges",
    "custom_hotel_refund_amount",
    "custom_hotel_reschedule_details",
    "custom_hotel_reschedule_charges",
    "custom_rescheduled_hotel_ticket_",
    "custom_hotel_preferences",
    "custom_laundry_facility",
    "custom_laundry_facility_remarks",
    "custom_discount_on_meal",
    "custom_meal_discount_remarks",
    "custom_airport_transport",
    "custom_airport_transport_remarks",
    "custom_break_fast",
    "custom_wifi",
    "custom_hotel_invoice_details",
    "custom_hotel_invoice_id",
    "custom_hotel_booking_vendor_name",
    "custom_service_category",
    "custom_payment_terms_for_hotel_booking",
    "custom_hotel_cost_per_day",
    "custom_total_hotel_charge",
    "custom_total_hotel_charge_as_per_invoice",
    "custom_hotel_payment_status",
    "custom_paid_amount_hotel",
    "custom_outstanding_amount_hotel",
    "custom_create_purchase_invoice_hotel",
    "custom_send_email_hotel",
]

TAXI_DOCTYPE = "Travel Taxi Details"
TAXI_CHECKBOX = "custom_taxi_required"
TAXI_GATED_FIELDS = [
    "taxi_coast",
    "custom_driver_contact_number",
    "custom_taxi_type",
    "custom_airport_transfer",
    "custom_daily_transfer",
    "custom_out_of_india",
    "custom_taxi_number",
    "custom_driver_name",
    "custom_taxi_invoice_attachment",
    "custom_daily_transfer_taxi_cost",
    "custom_taxi_invoice_details",
    "custom_taxi_invoice_id",
    "custom_service_item",
    "custom_taxi_vendor",
    "custom_create_purchase_invoice",
    "custom_send_email",
]


def execute():
    create_custom_fields(
        {
            HOTEL_DOCTYPE: [
                {
                    "fieldname": HOTEL_CHECKBOX,
                    "label": "Stay Required",
                    "fieldtype": "Check",
                    "insert_after": "employee_name",
                    "default": "0",
                }
            ],
            TAXI_DOCTYPE: [
                {
                    "fieldname": TAXI_CHECKBOX,
                    "label": "Taxi Required",
                    "fieldtype": "Check",
                    "insert_after": "segment_no",
                    "default": "0",
                }
            ],
        }
    )

    _set_depends_on(HOTEL_DOCTYPE, HOTEL_GATED_FIELDS, HOTEL_CHECKBOX)
    _set_depends_on(TAXI_DOCTYPE, TAXI_GATED_FIELDS, TAXI_CHECKBOX)

    frappe.clear_cache(doctype=HOTEL_DOCTYPE)
    frappe.clear_cache(doctype=TAXI_DOCTYPE)


def _set_depends_on(doctype, fieldnames, checkbox_fieldname):
    for field_name in fieldnames:
        if not frappe.get_meta(doctype).has_field(field_name):
            continue

        name = f"{doctype}-{field_name}-depends_on"
        if frappe.db.exists("Property Setter", name):
            continue

        frappe.get_doc(
            {
                "doctype": "Property Setter",
                "doctype_or_field": "DocField",
                "doc_type": doctype,
                "field_name": field_name,
                "property": "depends_on",
                "property_type": "Data",
                "value": f"eval:doc.{checkbox_fieldname}",
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()

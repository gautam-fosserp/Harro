# Copyright (c) 2025, Fosserp and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_link_to_form


@frappe.whitelist()
def create_travel_plan(names):
	travel_request = eval(names)
	skipped = []
	to_create = []

	for req in travel_request:
		plan = frappe.db.get_value(
			"Travel Planning Employee Details",
			{"travel_request": req},
			"parent"
		)
		if plan:
			skipped.append((req, plan))
		else:
			to_create.append(req)

	if not to_create:
		msg = "<p>Travel Planning already exists for selected requests:</p><ul>"
		for req, plan in skipped:
			msg += f"<li>{get_link_to_form('Travel Request', req)} → {get_link_to_form('Travel Planning', plan)}</li>"
		msg += "</ul>"
		frappe.throw(msg)

	travel_plan = frappe.new_doc("Travel Planning")
	for req in to_create:
		tr_doc = frappe.get_doc("Travel Request", req)
		# if tr_doc.docstatus < 1:
		# 	frappe.throw(
		# 		"Travel Request should be submitted.<br><ul><li>{0}</li></ul>".format(
		# 			get_link_to_form('Travel Request', req)
		# 		)
		# 	)
		if tr_doc.docstatus == 0:
			tr_doc.workflow_state = "Trip Planned"
			tr_doc.save(ignore_permissions=True)

		if len(tr_doc.itinerary):
			for tr in tr_doc.itinerary:
				travel_plan.append("travel_itinerary", {
					"travel_request" : tr_doc.name,
					"employee_hh_id" : tr_doc.employee,
					"employee_name" : tr_doc.employee_name,
					"travel_from" : tr.travel_from,
					"travel_to" : tr.travel_to,
					"mode_of_travel" : tr.mode_of_travel,
					"extra_baggage" : tr.custom_extra_baggage,
					"check_in_date" : tr.check_in_date,
					"check_out_date" : tr.check_out_date,
					"room_night" : tr.room_night,
					"lodging_required" : tr.lodging_required,
					"preferred_area_for_lodging" : tr.preferred_area_for_lodging,
					"travel_request_itinerary": tr.name,
					"custom_onward_travel_date": tr.custom_onward_travel_date,
					"custom_return_travel_date": tr.custom_return_travel_date,
					"custom_taxi_required": tr.custom_taxi_required
				})
		else:
			travel_plan.append("travel_itinerary", {
				"travel_request" : tr_doc.name,
				"employee_hh_id" : tr_doc.employee,
				"employee_name" : tr_doc.employee_name,
			})
	
	if employee := frappe.db.exists("Employee", {"user_id" : frappe.session.user}):
			travel_plan.travel_requestor = employee

	travel_plan.travel_type = tr_doc.travel_type
	travel_plan.purpose_of_travel = tr_doc.purpose_of_travel

	if travel_request:
		travel_plan.ba_number = tr_doc.custom_ba_number

	if to_create:
		travel_plan.ba_number = tr_doc.custom_ba_number

	travel_plan.insert()

	msg = "<p>Travel Planning Created:</p>"
	msg += f"<ul><li>{get_link_to_form('Travel Planning', travel_plan.name)}</li></ul>"

	if skipped:
		msg += "<p><b>Information:</b> A Travel Plan already exists for the following Travel Requests : </p><ul>"
		for req, plan in skipped:
			msg += f"<li>{get_link_to_form('Travel Request', req)} → {get_link_to_form('Travel Planning', plan)}</li>"
		msg += "</ul>"

	frappe.msgprint(msg)



def calculate_totals(doc, method=None):
	if not doc.travel_itinerary:
		return

	field_map = {
		"custom_total_flight_cost_as_per_invoice": "total_flight_coast",
		"custom_total_hotel_charge_as_per_invoice": "total_hotel_booking_coast",
		"baggage_coast": "total_currency_coast",
		"custom_seat_charges": "custom_total_seat_charges",
		"taxi_coast": "total_taxi_coast",
		"custom_flight_cancellation_charges": "custom_total_flight_cancellation_charges",
		"custom_flight_refund_amount": "custom_total_flight_refund_amount",
		"custom_flight_reschedule_charges": "custom_total_flight_reschedule_charges",
	}

	for child_field, parent_field in field_map.items():
		doc.set(parent_field, sum((d.get(child_field) or 0) for d in doc.travel_itinerary))

	# Additional travel segments (Travel Flight Details / Travel Hotel Booking / Travel Taxi Details)
	# are independent DocTypes, not child tables, so they must be queried rather than iterated from doc.get(...).
	if not doc.is_new():
		additional_flight_cost = frappe.db.get_value(
			"Travel Flight Details",
			{"travel_planning": doc.name},
			"sum(custom_total_flight_cost_as_per_invoice)",
		) or 0
		additional_hotel_cost = frappe.db.get_value(
			"Travel Hotel Booking",
			{"travel_planning": doc.name},
			"sum(custom_total_hotel_charge_as_per_invoice)",
		) or 0
		additional_taxi_cost = frappe.db.get_value(
			"Travel Taxi Details",
			{"travel_planning": doc.name},
			"sum(taxi_coast)",
		) or 0

		doc.total_flight_coast = (doc.total_flight_coast or 0) + additional_flight_cost
		doc.total_hotel_booking_coast = (doc.total_hotel_booking_coast or 0) + additional_hotel_cost
		doc.total_taxi_coast = (doc.total_taxi_coast or 0) + additional_taxi_cost

	total_claimable = 0
	total_unclaimable = 0

	for d in doc.travel_itinerary:
		row_total = (
			# (d.baggage_coast or 0)
			# + (d.custom_seat_charges or 0)
			+ (d.custom_total_flight_cost_as_per_invoice or 0)
			+ (d.custom_total_hotel_charge_as_per_invoice or 0)
			+ (d.taxi_coast or 0)
		)

		# reset values to avoid leftover data
		d.custom_total_claimable_amount = 0
		d.custom_total_unclaimable_amount = 0

		if d.custom_is_claimable:
			d.custom_total_claimable_amount = row_total
			total_claimable += row_total

		elif d.custom_not_claimable:
			d.custom_total_unclaimable_amount = row_total
			total_unclaimable += row_total

	# Set parent totals
	doc.custom_total_claimable_expense = total_claimable
	doc.custom_total_unclaimable_expense = total_unclaimable


# View only logged in user linked employee rows in travelling planning child table(travel iternary)
VIEW_ALL_ROLES = {
    "Travel Manager",
    "Travel User",
    "Travel Desk Manager",
    "Accounts Manager",
    "Accounts User",
    "System Manager",
}

def _can_view_all(user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return bool(set(frappe.get_roles(user)) & VIEW_ALL_ROLES)

def _get_linked_employee(user=None):
    user = user or frappe.session.user
    return frappe.db.get_value("Employee", {"user_id": user}, "name")

def filter_itinerary_rows_by_employee(doc, method=None):
    """Show only the logged-in user's own row unless they hold a
    view-all role."""
    if _can_view_all():
        return

    employee = _get_linked_employee()
    if not employee:
        doc.travel_itinerary = []
        return

    doc.travel_itinerary = [
        row for row in doc.travel_itinerary
        if row.custom_employee == employee
    ]


def restore_hidden_rows_before_save(doc, method=None):
	"""Safety net: if this user only ever saw their own row (others were
    stripped in onload), re-merge the untouched rows from the DB version
    before save so we don't wipe out other employees' data."""

	if _can_view_all():
		return
	if doc.is_new():
		return
	db_doc = frappe.get_doc(doc.doctype, doc.name)
	visible_ids = {row.custom_employee for row in doc.travel_itinerary}

	for row in db_doc.travel_itinerary:
		if row.custom_employee not in visible_ids:
			doc.append("travel_itinerary", row.as_dict())

	
def employee_row_permission_query(user):
    """Row-level filter for direct queries against the child doctype
    (Report Builder, frappe.client.get_list, etc.)."""
    if not user:
        user = frappe.session.user
    if _can_view_all(user):
        return ""

    employee = _get_linked_employee(user)
    if not employee:
        return "1=0"

    return f"`tabTravel Planning Employee Details`.custom_employee = {frappe.db.escape(employee)}"


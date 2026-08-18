// Copyright (c) 2026, Fosserp and contributors
// For license information, please see license.txt

frappe.ui.form.on("Travel Flight Details", {
    refresh(frm) {
        frm.__old_onward = frm.doc.custom_onward_travel_date;
        frm.__old_return = frm.doc.custom_return_travel_date;
        travel_segment_add_back_button(frm);
    },
    custom_create_purchase_invoice_flight(frm) {
        const create_invoice = () => {
            frappe.call({
                method: "harro.harro.doctype.travel_flight_details.travel_flight_details.make_purchase_invoice",
                args: {
                    source_name: frm.doc.name
                },
                freeze: true,
                freeze_message: __("Creating Purchase Invoice..."),
                callback(r) {
                    if (r.message) {
                        frappe.model.sync(r.message);
                        frappe.set_route(
                            "Form",
                            "Purchase Invoice",
                            r.message.name
                        );
                    }
                },
            });
        };
        if (frm.is_dirty()) {
            frm.save().then(create_invoice);
        } else {
            create_invoice();
        }
    },
    custom_send_email_flight(frm) {
        if (frm.doc.custom_flight_email_sent) {
            frappe.msgprint("Email already sent for this record.");
            return;
        }
        frappe.call({
            method: "harro.harro.doctype.travel_planning.travel_planning.send_flight_segment_email",
            args: { name: frm.doc.name },
            callback(r) {
                if (!r.exc) {
                    frappe.msgprint("Email sent");
                    frm.reload_doc();
                }
            },
        });
    },
    custom_send_revised_ticket(frm) {
        send_reschedule_ticket(frm, "first");
    },
    custom_send_second_reschedule_ticket(frm) {
        send_reschedule_ticket(frm, "second");
    },
    custom_send_credit_note(frm) {
        frappe.confirm(
            __("Are you sure you want to send the Credit Note email?"),
            () => {
                const send = () => {
                    frappe.call({
                        method: "harro.harro.doctype.travel_flight_details.travel_flight_details.send_credit_note_email",
                        args: { docname: frm.doc.name },
                        freeze: true,
                        freeze_message: "Sending email...",
                        callback(r) {
                            if (!r.exc) {
                                frappe.show_alert({ message: "Credit Note email sent", indicator: "green" });
                            }
                        },
                    });
                };
                if (frm.is_dirty()) {
                    frm.save().then(send);
                } else {
                    send();
                }
            }
        )
    },
    custom_onward_travel_date(frm) {
        if (frm.is_new()) return;

        prompt_for_comment(
            frm,
            "Onward Travel Date",
            frm.__old_onward,
            frm.doc.custom_onward_travel_date
        );
        
        frm.__old_onward = frm.doc.custom_onward_travel_date;
    },

    custom_return_travel_date(frm) {
        if (frm.is_new()) return;

        prompt_for_comment(
            frm,
            "Return Travel Date",
            frm.__old_return,
            frm.doc.custom_return_travel_date
        );

        frm.__old_return = frm.doc.custom_return_travel_date;
    },
    custom_send_first_rescheduling_invoice: function(frm) {
        send_invoice_email(frm, 'first');
    },

    custom_send_second_rescheduling_invoice: function(frm) {
        send_invoice_email(frm, 'second');
    },
    custom_send_first_reschedule_request: function(frm) {
        send_reschedule_request(frm, 'first');
    },
    custom_send_second_reschedule_request: function(frm) {
        send_reschedule_request(frm, 'second');
    },
    custom_seat_charges: function(frm) {
        calculate_total_flight_cost(frm);
    },
    baggage_coast: function(frm) {
        calculate_total_flight_cost(frm);
    },
    custom_onward_flight_cost_as_per_invoice: function(frm) {
        calculate_total_flight_cost(frm);
    },
    custom_return_flight_cost_as_per_invoice: function(frm) {
        calculate_total_flight_cost(frm);
    },
    custom_round_trip_cost_as_per_invoice: function(frm) {
        calculate_total_flight_cost(frm);
    },
    custom_create_onward_flight_invoice: function(frm) {
        frappe.call({
            method: 'harro.harro.doctype.travel_flight_details.travel_flight_details.make_onward_flight_purchase_invoice',
            args: {
                source_name: frm.doc.name
            },
            freeze: true,
            freeze_message: __("Creating Purchase Invoice..."),
            callback(r) {
                if (r.message) {
                    frappe.model.sync(r.message);

                    frappe.set_route(
                        "Form",
                        "Purchase Invoice",
                        r.message.name
                    );
                }
            }
        });
    },
    custom_send_cancellation_request: function(frm) {
        const send = () => {
            frappe.call({
                method: "harro.harro.doctype.travel_flight_details.travel_flight_details.send_cancellation_request_email",
                args: {
                    source_name: frm.doc.name
                },
                freeze: true,
                freeze_message: __("Sending email..."),
                callback(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __("Cancellation Request email sent"),
                            indicator: "green"
                        });
                    }
                }
            });
        };

        if (frm.is_dirty()) {
            frm.save().then(send);
        } else {
            send();
        }
    }
});

function send_reschedule_ticket(frm, request_type) {
    if (frm.is_new() || frm.is_dirty()) {
        frappe.msgprint('Please save the document before sending then email');
        return;
    }

    const label = request_type === 'first' ? 'First' : 'second';
    
    frappe.confirm(
        `Send ${label} Rescheduling ticket to the traveller ?`,
        function() {
            frappe.call({
                method: 'harro.harro.doctype.travel_flight_details.travel_flight_details.send_reschedule_ticket',
                args: {
                    docname: frm.doc.name,
                    request_type: request_type
                },
                freeze: true,
                freeze_message: 'Sending email...',
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({message: `${label} Rescheduling Request sent`, indicator: 'green'});
                    }
                }
            })
        }
    )
}

function send_reschedule_request(frm, request_type) {
    if (frm.is_new() || frm.is_dirty()) {
        frappe.msgprint('Please save the document before sending the email.')
        return;
    }

    const label = request_type == 'first' ? 'First' : 'Second';
    frappe.confirm(
        `Send ${label} Rescheduling Request email to the Travel Manager?`,
        function() {
            frappe.call({
                method: 'harro.harro.doctype.travel_flight_details.travel_flight_details.send_reschedule_request',
                args: {
                    docname: frm.doc.name,
                    request_type: request_type
                },
                freeze: true,
                freeze_message: 'Sending email...',
                callback: function(r) {
                    if(!r.exc) {
                        frappe.show_alert({message: `${label} Rescheduling Invoice sent`, indicator: 'green'});
                    }
                }
            });
        }
    );
}

function send_invoice_email(frm, invoice_type) {
    if (frm.is_new() || frm.is_dirty()) {
        frappe.msgprint('Please save the document before sending the email.');
        return;
    }

    const label = invoice_type === 'first' ? 'First' : 'Second';
    const attach_field = invoice_type === 'first'
        ? 'custom_rescheduling_invoice'
        : 'custom_second_rescheduling_invoice';

    if (!frm.doc[attach_field]) {
        frappe.msgprint(`Please attach the ${label} Rescheduling Invoice first.`);
        return;
    }

    frappe.confirm(
        `Send ${label} Rescheduling Invoice email to the Accounts team?`,
        function() {
            frappe.call({
                method: 'harro.harro.doctype.travel_flight_details.travel_flight_details.send_rescheduling_invoice_email',
                args: {
                    docname: frm.doc.name,
                    invoice_type: invoice_type
                },
                freeze: true,
                freeze_message: 'Sending email...',
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({message: `${label} Rescheduling Invoice sent`, indicator: 'green'});
                    }
                }
            });
        }
    );
}

function prompt_for_comment(frm, field_name, old_value, new_value) {

    let d = new frappe.ui.Dialog({
        title: __("Reason for Travel Date Change"),
        fields: [
            {
                fieldname: "comment",
                fieldtype: "Small Text",
                label: __("Reason"),
                reqd: 1
            }
        ],
        primary_action_label: __("Submit"),
        primary_action(values) {

            frappe.call({
                method: "harro.harro.doctype.travel_flight_details.travel_flight_details.add_travel_date_comment",
                args: {
                    docname: frm.doc.name,
                    field_name: field_name,
                    old_value: old_value,
                    new_value: new_value,
                    comment: values.comment
                },
                callback() {
                    d.hide();
                }
            });

        }
    });

    d.show();
}

function travel_segment_add_back_button(frm) {
    if (!frm.doc.travel_planning) return;
    const label = __("<-- Back to Travel Planning");
    frm.add_custom_button(label, () => go_back_to_travel_planning(frm));
    style_back_button(frm, label);
}

function go_back_to_travel_planning(frm) {
    const travel_planning = frm.doc.travel_planning;
    const travel_itinerary_row = frm.doc.travel_itinerary_row;

    const navigate = () => {
        frappe.route_options = { open_itinerary_row: travel_itinerary_row };
        frappe.set_route("Form", "Travel Planning", travel_planning);
    };

    if (frm.is_new() || frm.is_dirty()) {
        frm.save().then(navigate);
    } else {
        navigate();
    }
}

function style_back_button(frm, label) {
    if (!document.getElementById("tp-back-btn-style")) {
        const style = document.createElement("style");
        style.id = "tp-back-btn-style";
        style.textContent = `
            .btn-back-to-travel-planning {
                background: #fbdcdc !important;
                border-color: #f3b7b7 !important;
                color: #8a2b2b !important;
            }
            .btn-back-to-travel-planning:hover {
                background: #f7c6c6 !important;
            }
        `;
        document.head.appendChild(style);
    }
    frm.page.inner_toolbar
        .find(`button[data-label="${encodeURIComponent(label)}"]`)
        .addClass("btn-back-to-travel-planning");
}

function calculate_total_flight_cost(frm) {
    const onward_flight_cost = flt(frm.doc.custom_onward_flight_cost_as_per_invoice || 0);
    const return_flight_cost = flt(frm.doc.custom_return_flight_cost_as_per_invoice || 0);
    const seat_charge = flt(frm.doc.custom_seat_charges || 0);
    const baggage_cost = flt(frm.doc.baggage_coast || 0);
    const round_trip_cost = flt(frm.doc.custom_round_trip_cost_as_per_invoice || 0);

    const total_flight_cost = (onward_flight_cost+return_flight_cost+seat_charge+baggage_cost+round_trip_cost);

    frm.set_value("custom_total_flight_cost_as_per_invoice", total_flight_cost);
}
// Copyright (c) 2026, Fosserp and contributors
// For license information, please see license.txt

frappe.ui.form.on("Travel Flight Details", {
    refresh(frm) {
        frm.__old_onward = frm.doc.custom_onward_travel_date;
        frm.__old_return = frm.doc.custom_return_travel_date;
        travel_segment_hide_sidebar(frm);
        travel_segment_add_back_button(frm);
    },
    custom_create_purchase_invoice_flight(frm) {
        const create_invoice = () => {
            frappe.call({
                method: "harro.harro.doctype.travel_planning.travel_planning.get_flight_segment_purchase_invoice_defaults",
                args: { name: frm.doc.name },
                callback(r) {
                    if (r.message) {
                        frappe.set_route("Form", "Purchase Invoice", r.message);
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
    }
});

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

function travel_segment_hide_sidebar(frm) {
    if (frm.sidebar) {
        frm.sidebar.sidebar.toggle(false);
        frm.page.sidebar.addClass("hide-sidebar");
    }
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

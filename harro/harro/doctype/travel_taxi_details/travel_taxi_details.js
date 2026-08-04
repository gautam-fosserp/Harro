// Copyright (c) 2026, Fosserp and contributors
// For license information, please see license.txt

frappe.ui.form.on("Travel Taxi Details", {
    refresh(frm) {
        travel_segment_hide_sidebar(frm);
        travel_segment_add_back_button(frm);
    },
    custom_create_purchase_invoice(frm) {
        const create_invoice = () => {
            frappe.call({
                method: "harro.harro.doctype.travel_planning.travel_planning.get_taxi_segment_purchase_invoice_defaults",
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
    custom_send_email(frm) {
        if (frm.doc.custom_taxi_email_sent) {
            frappe.msgprint("Email already sent for this record.");
            return;
        }
        frappe.call({
            method: "harro.harro.doctype.travel_planning.travel_planning.send_taxi_segment_email",
            args: { name: frm.doc.name },
            callback(r) {
                if (!r.exc) {
                    frappe.msgprint("Email sent");
                    frm.reload_doc();
                }
            },
        });
    },
});

function travel_segment_hide_sidebar(frm) {
    if (frm.sidebar) {
        frm.sidebar.sidebar.toggle(false);
        frm.page.sidebar.addClass("hide-sidebar");
    }
}

function travel_segment_add_back_button(frm) {
    if (!frm.doc.travel_planning) return;
    const label = __("Back to Travel Planning");
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

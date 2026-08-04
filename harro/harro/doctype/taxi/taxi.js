// Copyright (c) 2025, Fosserp and contributors
// For license information, please see license.txt

frappe.ui.form.on("Taxi", {
	refresh(frm) {
        if (!frm.is_new()) {
            if (frm.doc.workflow_state === "Waiting for Payment") {
                frm.add_custom_button(__("Purchase Invoice"), (frm)=>{
                frappe.model.open_mapped_doc({
                    method: "harro.harro.doctype.taxi.taxi.create_purchase_invoice",
                    frm: cur_frm,
                });
            }, __("Create"))
            }
        }
	},
    custom_package(frm) {
        calculate_cost(frm);
    },

    custom_extra_hour_amount(frm) {
        calculate_cost(frm);
    },
    custom_toll_tax(frm) {
        calculate_cost(frm);
    },
    taxi_requestor: function(frm) {
        if (frm.doc.taxi_requestor) {
            frappe.db.get_value(
                "Employee",
                frm.doc.taxi_requestor,
                "reports_to"
            ).then(r => {
                if (r.message && r.message.reports_to) {
                    console.log(r.message);
                    frappe.db.get_value(
                        "Employee",
                        r.message.reports_to,
                        "user_id"
                    ).then(res => {
                        if (res.message && res.message.user_id) {
                            frm.set_value(
                                "taxi_requestor_team_lead",
                                res.message.user_id
                            );
                        } else {
                            frm.set_value("taxi_requestor_team_lead", "");
                        }
                    })
                }
            })
        }
    }
});



function calculate_cost(frm) {
    let package_amount = frm.doc.custom_package || 0;
    let extra_hour_amount = frm.doc.custom_extra_hour_amount || 0;
    let toll_tax = frm.doc.custom_toll_tax || 0;

    let cost = package_amount + extra_hour_amount + toll_tax;
    frm.set_value("cost", cost);
}
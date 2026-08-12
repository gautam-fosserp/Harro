// Copyright (c) 2026, Fosserp and contributors
// For license information, please see license.txt

frappe.ui.form.on("Visa Request", {
	refresh(frm) {
        hide_child_table(frm);
        // change "To Applicant" label to employee_name
        if (frm.doc.employee_name) {
            frm.set_df_property(
                "to_applicant",
                "label",
                `To ${frm.doc.employee_name}`
            );
            frm.refresh_field("to_applicant");
        }

        if (!frm.is_new() && frm.doc.workflow_state === "Waiting for Payment") {
            frm.add_custom_button(__("Purchase Invoice"), (frm) => {
                frappe.model.open_mapped_doc({
                    method: "harro.harro.doctype.visa_request.visa_request.create_purchase_invoice",
                    frm: cur_frm
                });
            }, __("Create"))
        }
        frm.set_query("visa_checklist", function(doc){
            return {
                filters: {
					country: doc.visa_country,
				},
            }
        })
        set_employee_filter(frm);
	},
    visa_country(frm) {
        if (!frm.doc.visa_country) return;

        frappe.db.get_value(
            'Country Wise visa Document Checklist',
            { country: frm.doc.visa_country },
            'name'
        ).then(r => {
            if (r.message) {
                console.log(r.message)
                frm.set_value('visa_checklist', r.message.name);
            } else {
                frm.set_value('visa_checklist', null);
                frappe.msgprint(__('No checklist found for selected country'));
            }
        });
    },
    visa_checklist: (frm) => {
        if (frm.doc.visa_checklist) {
            frappe.call({
                method: "harro.harro.doctype.visa_request.visa_request.get_visa_check_list_details",
                args: {
                    chekck_list: frm.doc.visa_checklist
                },
                callback: (r) => {
                    if (r.message) {
                        // Clear all three tables
                        frm.doc.check_list = [];
                        frm.doc.custom_documents_inviting_company = [];
                        frm.doc.custom_documents_harro = [];

                        // Documents (Traveller)
                        (r.message.checklist || []).forEach(e => {
                            let row = frm.add_child("check_list");
                            row.catogory = e.catogory;
                            row.checklistname_of_document = e.checklistname_of_document;
                            row.options = e.options;
                        });

                        // Documents (Inviting Company)
                        (r.message.custom_documents_inviting_company || []).forEach(e => {
                            let row = frm.add_child("custom_documents_inviting_company");
                            row.checklistname_of_document = e.checklistname_of_document;
                        });

                        // Documents (Harro) — from custom_visa_checklist_for_travel_manager
                        (r.message.custom_documents_harro || []).forEach(e => {
                            let row = frm.add_child("custom_documents_harro");
                            row.checklistname_of_document = e.checklistname_of_document;
                        });

                        frm.refresh_field("check_list");
                        frm.refresh_field("custom_documents_inviting_company");
                        frm.refresh_field("custom_documents_harro");
                    }
                }
            });
        }
    },
    employee_name: function(frm) {
        if (frm.doc.employee_name) {
            frm.set_df_property(
                "to_applicant",
                "label",
                `To ${frm.doc.employee_name}`
            );
            frm.refresh_field("to_applicant");
        }
    },
    employee_id(frm) {
        hide_child_table(frm);
    }
});


function hide_child_table(frm) {
    const user_roles = frappe.user_roles || [];

    const restricted_roles = [
        "Managing Director",
        "Operation Department Head"
    ];

    const is_restricted_role = restricted_roles.some(role =>
        user_roles.includes(role)
    );

    // Restricted roles cannot see any child table
    if (is_restricted_role) {
        set_child_tables_visibility(frm, false);
        return;
    }

    if (!frm.doc.employee_id) {
        set_child_tables_visibility(frm, false);
        return;
    }

    frappe.db.get_value(
        "Employee",
        frm.doc.employee_id,
        "user_id"
    ).then(r => {
        const employee_user = r.message?.user_id;

        const is_self_request =
            employee_user === frappe.session.user;

        if (is_self_request) {
            // Self request:
            // Show only Documents (Traveller)
            set_child_tables_visibility(frm, true);
        } else {
            // Request for another employee:
            // Hide all child tables
            set_child_tables_visibility(frm, false);
        }
    });
}


function set_child_tables_visibility(frm, show_traveller) {
    // Documents (Traveller)
    frm.set_df_property(
        "check_list",
        "hidden",
        show_traveller ? 0 : 1
    );

    // Documents (Inviting Company)
    frm.set_df_property(
        "custom_documents_inviting_company",
        "hidden",
        1
    );

    // Documents (Harro)
    frm.set_df_property(
        "custom_documents_harro",
        "hidden",
        1
    );

    //heading
    frm.set_df_property(
        "custom_please_provide_hard_copy_of_documents_to_travel_desk",
        "hidden",
        show_traveller ? 0 : 1
    );

    frm.refresh_field("check_list");
    frm.refresh_field("custom_documents_inviting_company");
    frm.refresh_field("custom_documents_harro");
    frm.refresh_field(
        "custom_please_provide_hard_copy_of_documents_to_travel_desk"
    );
}

function set_employee_filter(frm) {
    if (frm._employee_filter_set) return;

    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Employee',
            filters: { user_id: frappe.session.user },
            fieldname: 'name'
        },
        callback: function(response) {
            const logged_in_employee = response && response.message && response.message.name;

            if (!logged_in_employee) {
                frm.set_query('employee_id', function() {
                    return { filters: { name: ['in', []] } };
                });
                frm._employee_filter_set = true;
                setTimeout(() => {
                    frappe.msgprint({
                        title: __('Warning'),
                        message: __('No Employee record found for the logged-in user. You cannot create a Visa Request.'),
                        indicator: 'orange'
                    });
                }, 500);
                return;
            }

            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Employee',
                    filters: [
                        ['reports_to', '=', logged_in_employee],
                        ['status', '=', 'Active']
                    ],
                    fieldname: 'name',
                    limit: 0
                },
                callback: function(r) {
                    if (!r || r.exc) {
                        frappe.show_alert({
                            message: __('Failed to load employee list. Please refresh.'),
                            indicator: 'red'
                        });
                        return;
                    }

                    const direct_reports = (r.message || []).map(e => e.name);
                    const allowed = [logged_in_employee, ...direct_reports];

                    frm.set_query('employee_id', function() {
                        return {
                            filters: [
                                ['name', 'in', allowed],
                                ['status', '=', 'Active']
                            ]
                        };
                    });

                    frm.refresh_field('employee_id');
                    frm._employee_filter_set = true;
                }
            });
        }
    });
}

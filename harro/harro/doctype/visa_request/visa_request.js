// Copyright (c) 2026, Fosserp and contributors
// For license information, please see license.txt

frappe.ui.form.on("Visa Request", {
	refresh(frm) {
        frm.set_query("visa_checklist", function(doc){
            return {
                filters: {
					country: doc.visa_country,
				},
            }
        })
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
    visa_checklist:(frm)=>{
        if (frm.doc.visa_checklist){
            frappe.call({
                method : "harro.harro.doctype.visa_request.visa_request.get_visa_check_list_details",
                args : {
                    chekck_list : frm.doc.visa_checklist
                },
                callback:(r)=>{
                    if(r.message){
                        frm.doc.check_list = []
                        r.message.checklist.forEach(e => {
                           let row = frm.add_child("check_list"); 
                           row.catogory = e.catogory
                           row.checklistname_of_document = e.checklistname_of_document
                           row.options = e.options
                        });
                        frm.refresh_field("check_list")
                    }
                }
            })
        }
    }
});

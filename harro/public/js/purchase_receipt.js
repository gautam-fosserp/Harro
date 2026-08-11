frappe.ui.form.on("Purchase Receipt", {
    refresh: function (frm) {
        
        // Bin Location Query
       frm.set_query("bin_location", "items", function(doc, cdt, cdn){
            let d = locals[cdt][cdn]
            if(!d.rack){
                frappe.throw("Source Rack is not selected")
            }
            return {
                query: "harro.harro.docevents.stock_entry.get_bin_location",
                filters: { rack : d.rack },
            };
        });

        // Rejected Bin Location Query
        frm.set_query("rejected_bin_location", "items", function(doc, cdt, cdn){
            let d = locals[cdt][cdn]
            if(!d.rejected_rack){
                frappe.throw("Rejected Rack is not selected")
            }
            return {
                query: "harro.harro.docevents.stock_entry.get_bin_location",
                filters: { rack : d.rejected_rack },
            };
        });
        
        // Generate payment schedule on refresh if missing
        if (
            frm.doc.docstatus === 0 &&
            frm.doc.custom_payment_terms_template &&
            (!frm.doc.custom_payment_schedule ||
             frm.doc.custom_payment_schedule.length === 0)
        ) {
            generate_payment_schedule(frm);
        }
	},
    cost_center : (frm)=>{
        if(frm.doc.cost_center){
            frm.doc.items.forEach(e => {
                frappe.model.set_value(e.doctype, e.name, "cost_center", frm.doc.cost_center)
            });
        }
    },
    project : (frm)=>{
        if(frm.doc.project){
            frm.doc.items.forEach(e => {
                frappe.model.set_value(e.doctype, e.name, "project", frm.doc.project)
            });
        }
    },
    custom_payment_terms_template(frm) {
        generate_payment_schedule(frm);
    },
    custom_customer_service :function(frm) {
	    if (frm.doc.custom_customer_service) {
		    console.log("Heyy");
		    frm.set_value("cost_center", "41630 - CS Spare Parts - Harro IN");
		}
		else {
		    frm.set_value("cost_center", "44010 - Purchasing - Harro IN");
		}
	}
})

frappe.ui.form.on('Purchase Receipt Item', {
    rack:function(frm, cdt, cdn){
        frm.set_query("bin_location", "items", function(doc, cdt, cdn){
            let d = locals[cdt][cdn]
            if(!d.rack){
                frappe.throw("Source Rack is not selected")
            }
            return {
                query: "harro.harro.docevents.stock_entry.get_bin_location",
                filters: { rack : d.rack },
            };
        })
    },
    rejected_rack:function(frm, cdt, cdn){
        frm.set_query("rejected_bin_location", "items", function(doc, cdt, cdn){
            let d = locals[cdt][cdn]
            if(!d.rejected_rack){
                frappe.throw("Rejected Rack is not selected")
            }
            return {
                query: "harro.harro.docevents.stock_entry.get_bin_location",
                filters: { rack : d.rejected_rack },
            };
        })
    }
});

function generate_payment_schedule(frm) {

    if (!frm.doc.custom_payment_terms_template) return;

    frappe.call({
        method: "erpnext.controllers.accounts_controller.get_payment_terms",
        args: {
            terms_template: frm.doc.custom_payment_terms_template,
            posting_date: frm.doc.posting_date || frappe.datetime.get_today(),
            grand_total: frm.doc.grand_total || 0,
            bill_date: frm.doc.bill_date || null
        },

        callback: function(r) {

            if (r.message) {

                // Clear old rows
                frm.clear_table("custom_payment_schedule");

                // Add new rows
                r.message.forEach(row => {

                    let child = frm.add_child("custom_payment_schedule");

                    child.payment_term = row.payment_term;
                    child.description = row.description;
                    child.due_date = row.due_date;
                    child.invoice_portion = row.invoice_portion;
                    child.payment_amount = row.payment_amount;
                });

                // Set last due date
                if (r.message.length > 0) {

                    frm.set_value(
                        "custom_due_date",
                        r.message[r.message.length - 1].due_date
                    );
                }

                frm.refresh_field("custom_payment_schedule");
            }
        }
    });
}

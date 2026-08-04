frappe.ui.form.on("BOM Creator", {
	custom_add_bom_items : function(frm){
        if (!frm.doc.custom_input_bom_file) {
            frappe.msgprint({
                title: __("File Required"),
                message: __("Please upload a BOM file first."),
                indicator: "orange"
            });
            return;
        }

        frappe.call({
            method: "harro.harro.docevents.bom_creator.extract_bom_item_data",
            args: { 
                file_path : frm.doc.custom_input_bom_file,
                bom_c : frm.doc.name
            },
            freeze: true,
			freeze_message: __("Please wait it will take some time ..."),
            callback(r) {
                if (r.message) {
                    frm.reload_doc()
                    frm.refresh_field("items")
                }
            }
        });
    },
    refresh:function(frm){
        if(frm.doc.items.length > 0){
            frm.set_df_property("custom_add_bom_items","hidden", 1)
        }
    }
});
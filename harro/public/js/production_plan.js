frappe.ui.form.on("Production Plan", {
    refresh: (frm) => {
        override_setup_download(frm);
        override_bulk_edit_functions(frm);
        frm.get_docfield("sub_assembly_items").allow_bulk_edit = true
        frm.fields_dict.sub_assembly_items.grid.setup_allow_bulk_edit()

        // filters for items_to_reduce_qty
        frm.set_query("items_to_reduce_qty", function () {
            let items = [];
            if (frm.doc.sub_assembly_items) {
                frm.doc.sub_assembly_items.forEach(row => {
                    if (row.production_item) {
                        items.push(row.production_item);
                    }
                });
            }
            // if no sub-assembly items, show nothing
            if (!items.length) {
                return {
                    filters: {
                        name: ["=", ""]
                    }
                }
            }
            return {
                filters: {
                    name: ["in", items]
                }
            }
        });
    },
    delete_selected_commodity_group_items(frm) {
        // collect commodity groups selected for removal
        let item_group_list = frm.doc.remove_based_item_group.map(e => e.commodity_group);

        // filter rows that should remain
        frm.doc.mr_items = frm.doc.mr_items.filter(row => {
            return !item_group_list.includes(row.commodity_group);
        });

        // reindex idx
        frm.doc.mr_items.forEach((row, index) => {
            row.idx = index + 1;   // Frappe child tables start at 1
        });

        frm.refresh_field("mr_items");
    },
    reduce_item_from_raw_material(frm) {
        if (!frm.doc.items_to_reduce_qty || !frm.doc.items_to_reduce_qty.length) {
            frappe.msgprint(__("Please select items to reduce quantity."));
            return;
        }
        if (frm.doc.__islocal){
            frappe.throw("Please save the document.")
        }
        frappe.confirm(
            __("This will reduce raw material quantities. Are you sure you want to continue ?"),
            () => {
                frappe.call({
                    method: "harro.harro.api.reduce_raw_material_qty",
                    args: {
                        production_plan: frm.doc.name,
                        items: frm.doc.items_to_reduce_qty
                    },
                    freeze: true,
                    callback() {
                        frm.reload_doc()
                        frappe.msgprint(__("Raw material quantities updated."));
                    }

                });
            }
        );
    }
})

function override_setup_download(frm) {
    let grid = frm.fields_dict.sub_assembly_items.grid;

    // override the method
    grid.setup_download = function () {
        let title = this.df.label || frappe.model.unscrub(this.df.fieldname);

        $(this.wrapper)
            .find(".grid-download")
            .removeClass("hidden")
            .off("click")                          // FIX added
            .on("click", () => {

                // ---- your corrected download code here ----

                var data = [];
                var docfields = [];

                data.push([__("Bulk Edit {0}", [title])]);
                data.push([]);
                data.push([]);
                data.push([]);
                data.push([__("The CSV format is case sensitive")]);
                data.push([__("Do not edit headers which are preset in the template")]);
                data.push(["------"]);

                $.each(frappe.get_meta(this.df.options).fields, (i, df) => {
                    if (frappe.model.is_value_type(df.fieldtype)) {
                        data[1].push(df.label);
                        data[2].push(df.fieldname);

                        let description = (df.description || "") + " ";
                        if (df.fieldtype === "Date") {
                            description += frappe.boot.sysdefaults.date_format;
                        }

                        data[3].push(description);
                        docfields.push(df);
                    }
                });

                $.each(frm.doc[this.df.fieldname] || [], (i, d) => {
                    var row = [];
                    $.each(data[2], (i, fieldname) => {
                        var value = d[fieldname];

                        if (docfields[i].fieldtype === "Date" && value) {
                            value = frappe.datetime.str_to_user(value);
                        }
                        row.push(value || "");
                    });
                    data.push(row);
                });

                frappe.tools.downloadify(data, null, title);
                return false;
            });
    };
}


function override_bulk_edit_functions(frm) {

    let grid = frm.fields_dict.sub_assembly_items.grid;

    // -------------------------------
    // 1️⃣ OVERRIDE setup_download()
    // -------------------------------
    grid.setup_download = function () {
        let title = this.df.label || frappe.model.unscrub(this.df.fieldname);

        $(this.wrapper)
            .find(".grid-download")
            .removeClass("hidden")
            .off("click")                                  // IMPORTANT FIX
            .on("click", () => {

                // ------- your original download code here -------
                // (keep same logic except .off)

                var data = [];
                var docfields = [];

                data.push([__("Bulk Edit {0}", [title])]);
                data.push([]);
                data.push([]);
                data.push([]);
                data.push([__("The CSV format is case sensitive")]);
                data.push([__("Do not edit headers which are preset in the template")]);
                data.push(["------"]);

                $.each(frappe.get_meta(this.df.options).fields, (i, df) => {
                    if (frappe.model.is_value_type(df.fieldtype)) {
                        data[1].push(df.label);
                        data[2].push(df.fieldname);

                        let description = (df.description || "") + " ";
                        if (df.fieldtype === "Date") {
                            description += frappe.boot.sysdefaults.date_format;
                        }

                        data[3].push(description);
                        docfields.push(df);
                    }
                });

                $.each(frm.doc[this.df.fieldname] || [], (i, d) => {
                    var row = [];
                    $.each(data[2], (i, fieldname) => {
                        var value = d[fieldname];

                        if (docfields[i].fieldtype === "Date" && value) {
                            value = frappe.datetime.str_to_user(value);
                        }

                        row.push(value || "");
                    });
                    data.push(row);
                });

                frappe.tools.downloadify(data, null, title);
                return false;
            });
    };

    // -------------------------------
    // 2️⃣ OVERRIDE setup_allow_bulk_edit()
    // -------------------------------
    grid.setup_allow_bulk_edit = function () {
        let me = this;

        if (this.frm && this.frm.get_docfield(this.df.fieldname)?.allow_bulk_edit) {

            // ensure download is overridden too
            this.setup_download();

            const value_formatter_map = {
                Date: (val) => (val ? frappe.datetime.user_to_str(val) : val),
                Int: (val) => cint(val),
                Check: (val) => cint(val),
                Float: (val) => flt(val),
                Currency: (val) => flt(val),
            };

            frappe.flags.no_socketio = true;

            $(this.wrapper)
                .find(".grid-upload")
                .removeClass("hidden")
                .off("click")                                 // IMPORTANT FIX
                .on("click", () => {

                    new frappe.ui.FileUploader({
                        as_dataurl: true,
                        allow_multiple: false,
                        restrictions: { allowed_file_types: [".csv"] },
                        on_success(file) {

                            var data = frappe.utils.csv_to_array(
                                frappe.utils.get_decoded_string(file.dataurl)
                            );

                            if (cint(data.length) - 7 > 5000) {
                                frappe.throw(__("Cannot import table with more than 5000 rows."));
                            }

                            var fieldnames = data[2];
                            me.frm.clear_table(me.df.fieldname);

                            $.each(data, (i, row) => {
                                if (i > 6) {
                                    var blank_row = true;

                                    $.each(row, function (ci, value) {
                                        if (value) {
                                            blank_row = false;
                                            return false;
                                        }
                                    });

                                    if (!blank_row) {
                                        var d = me.frm.add_child(me.df.fieldname);
                                        $.each(row, (ci, value) => {
                                            var fieldname = fieldnames[ci];
                                            var df = frappe.meta.get_docfield(
                                                me.df.options,
                                                fieldname
                                            );

                                            if (df) {
                                                d[fieldname] = value_formatter_map[df.fieldtype]
                                                    ? value_formatter_map[df.fieldtype](value)
                                                    : value;
                                            }
                                        });
                                    }
                                }
                            });

                            me.frm.refresh_field(me.df.fieldname);
                            frappe.msgprint({
                                message: __("Table updated"),
                                title: __("Success"),
                                indicator: "green",
                            });
                        },
                    });

                    return false;
                });
        }
    };
}

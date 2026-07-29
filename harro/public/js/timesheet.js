frappe.ui.form.on("Timesheet", {
    onload: function(frm) {
        if (frm.is_new() && !frm.doc.employee) {
            frappe.db.get_value(
                "Employee",
                {user_id: frappe.session.user},
                "name"
            ).then(r => {
                if (r.message && r.message.name) {
                    frm.set_value("employee", r.message.name);
                }
            });
        }
    }
});
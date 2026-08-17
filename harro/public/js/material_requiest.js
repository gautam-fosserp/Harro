frappe.ui.form.on("Material Request", {
    refresh(frm) {
        // Safety check for empty table
        const total_items = (frm.doc.items || []).length;

        // Clear old headline
        frm.dashboard.clear_headline();

        // Add improved alert
        frm.dashboard.set_headline_alert(`
            <div style="
                padding: 8px 12px;
                background: #eef6ff;
                border-left: 4px solid #1a73e8;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                color: #0b3558;
            ">
                Total Items in this Material Request: 
                <strong>${total_items}</strong>
            </div>
        `);
    }
});

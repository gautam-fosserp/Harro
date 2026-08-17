frappe.ui.form.on("Material Request", {
    refresh(frm) {
        apply_purpose_restriction(frm);
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
                color: #07233b;
            ">
                Total Items in this Material Request: 
                <strong>${total_items}</strong>
            </div>
        `);
    },
    onload: function(frm) {
        apply_purpose_restriction(frm);
    }
});


function apply_purpose_restriction(frm) {
    const roles = frappe.user_roles || [];
    const is_admin = roles.includes('Administrator') || roles.includes('System Manager');
    if (is_admin) return;

    let allowed = null;
    let default_value = null;
    let is_purchase_only = false;

    // Store/Stock role takes precedence over Purchase role when both are present
    if (roles.includes('Store In-Charge') || roles.includes('Stock Manager')) {
        allowed = ['Material Transfer', 'Material Issue', 'Manufacture'];
        default_value = 'Material Transfer';
    } else if (roles.includes('Purchase User') || roles.includes('Purchase Manager')) {
        allowed = ['Purchase'];
        default_value = 'Purchase';
        is_purchase_only = true;
    }

    if (!allowed) return;

    frm.set_df_property('material_request_type', 'options', allowed.join('\n'));
    frm.refresh_field('material_request_type');

    if (frm.is_new() && !frm.doc.material_request_type) {
        frm.set_value('material_request_type', default_value);
    }

    if (is_purchase_only && roles.includes('Purchase User') && !roles.includes('Purchase Manager')) {
        frm.set_df_property('material_request_type', 'read_only', 1);
    }
}




frappe.listview_settings['Material Request'] = {
    onload: function(listview) {
        const roles = frappe.user_roles || [];
        const is_admin = roles.includes('Administrator') || roles.includes('System Manager');
        if (is_admin) return;

        let allowed = null;
        // Store/Stock role takes precedence over Purchase role when both are present
        // (must match the precedence used in the Form Client Script)
        if (roles.includes('Store In-Charge') || roles.includes('Stock Manager')) {
            allowed = ['Material Transfer', 'Material Issue', 'Manufacture'];
        } else if (roles.includes('Purchase User') || roles.includes('Purchase Manager')) {
            allowed = ['Purchase'];
        }
        if (!allowed) return;

        const FIELD = 'material_request_type';
        const operator = allowed.length === 1 ? '=' : 'in';
        const value = allowed.length === 1 ? allowed[0] : allowed;

        // --- Popup filter (Filter → add condition → Purpose) ---
        const df = frappe.meta.get_docfield('Material Request', FIELD);
        if (df) {
            df.get_query = function() {
                return { filters: { name: ['in', allowed] } };
            };
        }
        let attempts = 0;
        const maxAttempts = 20;
        const interval = setInterval(function() {
            attempts++;
            const purpose_field = listview.page
                && listview.page.fields_dict
                && listview.page.fields_dict[FIELD];
            if (purpose_field) {
                purpose_field.df.options = allowed.join('\n');
                purpose_field.set_options
                    ? purpose_field.set_options(allowed.join('\n'))
                    : purpose_field.refresh();
                clearInterval(interval);
            } else if (attempts >= maxAttempts) {
                console.warn('material_request_type filter field not found after max attempts');
                clearInterval(interval);
            }
        }, 100);
        function pruneDropdown() {
            document.querySelectorAll('option, li.dropdown-item, a.dropdown-item').forEach(function(el) {
                const text = (el.textContent || '').trim();
                const isMRType = ['Purchase', 'Material Transfer', 'Material Issue',
                                   'Manufacture', 'Customer Provided'].includes(text);
                if (isMRType && !allowed.includes(text)) el.remove();
            });
        }
        const dropdown_observer = new MutationObserver(function() { pruneDropdown(); });
        dropdown_observer.observe(document.body, { childList: true, subtree: true });
        function apply_filter() {
            listview.filter_area.add([
                ['Material Request', FIELD, operator, value]
            ]);
        }

        // Apply on load
        apply_filter();

        // --- Block removal of this specific filter ---
        if (typeof listview.filter_area.remove === 'function') {
            const original_remove = listview.filter_area.remove.bind(listview.filter_area);
            listview.filter_area.remove = function(fieldname) {
                if (fieldname === FIELD) {
                    // Silently ignore attempts to remove the locked filter
                    return;
                }
                return original_remove(fieldname);
            };
        }

        // --- Block "Clear All" from wiping it too ---
        if (typeof listview.filter_area.clear === 'function') {
            const original_clear = listview.filter_area.clear.bind(listview.filter_area);
            listview.filter_area.clear = function() {
                original_clear();
                apply_filter();
            };
        }

        // --- Fallback safety net: re-check periodically in case some
        //     other code path removes it without going through the
        //     overridden methods above ---
        setInterval(function() {
            const current = listview.filter_area.get();
            const has_filter = current.some(f => f[1] === FIELD);
            if (!has_filter) apply_filter();
        }, 2000);
    }
};
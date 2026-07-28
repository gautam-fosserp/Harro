frappe.provide("frappe.listview_settings");

frappe.after_ajax(function () {
    const core_get_indicator = frappe.listview_settings["Purchase Order"].get_indicator;

    frappe.listview_settings["Purchase Order"].get_indicator = function (doc) {
        if (doc.status == "Partially Received and To Bill") {
            return [
                __("Partially Received and To Bill"),
                "yellow",
                "status,=,Partially Received and To Bill",
            ];
        }
        return core_get_indicator(doc);
    };
});
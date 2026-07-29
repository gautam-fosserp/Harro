frappe.ui.form.on("Timesheet", {
    setup: function (frm) {
        // Ensure core's timer.js is loaded before we touch it
        frappe.require("/assets/erpnext/js/projects/timer.js").then(() => {
            patch_timer_activity_type_filter();
        });
    }
});

function patch_timer_activity_type_filter() {
    if (erpnext.timesheet.timer.__custom_patched) return; // patch once

    erpnext.timesheet.timer = function (frm, row, timestamp = 0) {
        let dialog = new frappe.ui.Dialog({
            title: __("Timer"),
            fields: [
                {
                    fieldtype: "Link",
                    label: __("Activity Type"),
                    fieldname: "activity_type",
                    reqd: 1,
                    options: "Activity Type",
                    get_query: function () {
                        return {
                            query: "harro.harro.docevents.timesheet.get_employee_wise_activity",
                            filters: { employee: frm.doc.employee }
                        };
                    }
                },
                { fieldtype: "Link", label: __("Project"), fieldname: "project", options: "Project" },
                { fieldtype: "Link", label: __("Task"), fieldname: "task", options: "Task" },
                { fieldtype: "Float", label: __("Expected Hrs"), fieldname: "expected_hours" },
                { fieldtype: "Section Break" },
                { fieldtype: "HTML", fieldname: "timer_html" },
            ],
        });

        if (row) {
            dialog.set_values({
                activity_type: row.activity_type,
                project: row.project,
                task: row.task,
                expected_hours: row.expected_hours,
            });
        } else {
            dialog.set_values({ project: frm.doc.parent_project });
        }

        dialog.get_field("timer_html").$wrapper.append(get_timer_html());
        function get_timer_html() {
            return `
                <div class="stopwatch">
                    <span class="hours">00</span><span class="colon">:</span>
                    <span class="minutes">00</span><span class="colon">:</span>
                    <span class="seconds">00</span>
                </div>
                <div class="playpause text-center">
                    <button class="btn btn-primary btn-start"> ${__("Start")} </button>
                    <button class="btn btn-primary btn-complete"> ${__("Complete")} </button>
                </div>
            `;
        }

        // Untouched core engine — same function, not reimplemented
        erpnext.timesheet.control_timer(frm, dialog, row, timestamp);
        dialog.show();
    };

    erpnext.timesheet.timer.__custom_patched = true;
}
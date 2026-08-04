import frappe
from frappe import _
import json
from frappe.utils import getdate, get_last_day
from harro.harro.docevents.project import calculate_productive_working_hours


def get_or_create_month_timesheet(employee, project, company, from_time, time_log):
    log_date = getdate(from_time)
    month_start = log_date.replace(day=1)
    month_end = get_last_day(log_date)

    existing = frappe.db.get_value("Timesheet", {
        "employee": employee,
        "parent_project": project,
        "docstatus": 0,
        "start_date": ["between", [month_start, month_end]]
    }, "name")

    if existing:
        timesheet_doc = frappe.get_doc("Timesheet", existing)
        timesheet_doc.flags.ignore_permissions = True
        timesheet_doc.append("time_logs", time_log)
    else:
        timesheet_doc = frappe.get_doc({
            "doctype": "Timesheet",
            "employee": employee,
            "parent_project": project,
            "company": company,
            "start_date": month_start,
            "time_logs": [time_log]
        })
        timesheet_doc.flags.ignore_permissions = True

    return timesheet_doc


def validate(self, method):
    if self.project and not self.is_new():
        calculate_productive_working_hours(self.project)

def on_submit(self, method):
    if self.project:
        calculate_productive_working_hours(self.project)

def on_cancel(self, method):
    if self.project:
        calculate_productive_working_hours(self.project)


@frappe.whitelist()
def update_unproductive_log(arg, job_card):
    try:
        args = json.loads(arg)
    except:
        args = arg
    doc = frappe.get_doc("Job Card", job_card)

    employees = doc.employee

    if employees:
        for emp in employees:
            doc.append("custom_unproductive_work_timelogs", {
                "activity_type": args.get("activity_type"),
                "from_time": args.get("from_time"),
                "project": args.get("project"),
                "task": args.get("task"),
                "employee": emp.employee  # update employee field in child table row
            })
    else:
        # No employees → add single entry
        doc.append("custom_unproductive_work_timelogs", {
            "activity_type": args.get("activity_type"),
            "from_time": args.get("from_time"),
            "project": args.get("project"),
            "task": args.get("task"),
        })

    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True
    doc.save()

    return {"status": "success"}


@frappe.whitelist()
def resume_unproductive_log(to_time, job_card):
    doc = frappe.get_doc("Job Card", job_card)
    if not doc.project:
        frappe.throw(_("Project is required to create timesheet for unproductive work log. Add project to the job card and try again."))
    # Last log entry
    last_log = doc.custom_unproductive_work_timelogs[-1]
    last_log.to_time = to_time
    doc.flags.ignore_permissions = True

    employees = doc.get("employee") or []

    # If employees exist: create/reuse timesheet per employee
    if employees:
        for emp in employees:

            time_log = {
                "activity_type": last_log.get("activity_type"),
                "from_time": last_log.get("from_time"),
                "to_time": last_log.get("to_time"),
                "project": doc.project,
                "task": last_log.get("task"),
                "employee": emp
            }
            timesheet_doc = get_or_create_month_timesheet(
                emp, doc.project, doc.company, last_log.get("from_time"), time_log
            )

            if timesheet_doc.is_new():
                timesheet_doc.insert()
            else:
                timesheet_doc.save()
            timesheet_doc.submit()

            # Append a new row for each employee with reference
            doc.append("custom_unproductive_work_timelogs", {
                "activity_type": last_log.get("activity_type"),
                "from_time": last_log.get("from_time"),
                "to_time": last_log.get("to_time"),
                "project": doc.project,
                "task": last_log.get("task"),
                "employee": emp,
                "reference": timesheet_doc.name
            })

        # Remove the original last row (because now we inserted employee-wise rows)
        doc.custom_unproductive_work_timelogs.remove(last_log)

    else:
        # No employees → Single timesheet (existing logic)
        time_log = {
            "activity_type": last_log.get("activity_type"),
            "from_time": last_log.get("from_time"),
            "to_time": last_log.get("to_time"),
            "project": doc.project,
            "task": last_log.get("task"),
            "custom_ba_number": doc.project
        }
        timesheet_doc = get_or_create_month_timesheet(
            last_log.get("employee"), doc.project, doc.company, last_log.get("from_time"), time_log
        )

        if timesheet_doc.is_new():
            timesheet_doc.insert()
        else:
            timesheet_doc.save()
        timesheet_doc.submit()

        last_log.reference = timesheet_doc.name

    doc.save()

    return {"status": "success"}

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_operation_wise_activity(doctype, txt, searchfield, start, page_len, filters):
    filters = filters or {}

    custom_unproductive_work = 1 if filters.get("custom_unproductive_work") else 0

    operation = filters.get("operation")
    OPERATION_MAP = {
        "Mechanical Operation": "Mechanical",
        "Electrical Operation": "Electrical",
    }

    custom_job_card_type = OPERATION_MAP.get(operation)

    if not custom_job_card_type:
        frappe.msgprint(_("Unsupported Operation: {0}").format(operation))
        return []

    return frappe.db.sql(
        """
        SELECT at.name
        FROM `tabActivity Type` at
        WHERE
            IFNULL(at.custom_job_card_type, '') = %s
            AND IFNULL(at.custom_unproductive_work, 0) = %s
            AND at.name LIKE %s
        ORDER BY at.name
        LIMIT %s OFFSET %s
        """,
        (
            custom_job_card_type,
            custom_unproductive_work,
            f"%{txt}%",
            page_len,
            start,
        ),
    )

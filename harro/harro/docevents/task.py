import frappe
import json
from datetime import datetime
from frappe.utils import now, get_datetime, get_link_to_form, getdate, date_diff, get_last_day
from frappe.desk.form.assign_to import add as add_assignment
from frappe.desk.form.assign_to import set_status
from frappe import _



def validate(self, method=None):
    validate_parent_task_dates(self)
    validate_dependent_task_dates(self)
    if not self.custom_actual_progress:
        self.custom_actual_progress = "#FFC067"
    if not self.is_new():
        update_task_details_of_parent_task(self)
    
    if not self.custom_assigned_to_responsible_user and self.custom_employee__assign_to_employee_:
        user = frappe.db.get_value("Employee", self.custom_employee__assign_to_employee_, "user_id")
        self.custom_assigned_to_responsible_user = user
    
    if not self.custom_employee__assign_to_employee_ and self.custom_assigned_to_responsible_user:
        if employee := frappe.db.exists("Employee", {"user_id" : self.custom_assigned_to_responsible_user}):
            self.custom_employee__assign_to_employee_ = employee

    if self.exp_end_date and self.act_end_date:
        self.extra_days = get_extra_days(
                self.exp_end_date,
                self.act_end_date
            )
    update_department(self)
    remove_assignment_while_changing(self)

def after_insert(self, method):
    if task := frappe.db.exists("Task", {
        "status" : "Template",
        "is_milestone" : 1,
        "subject" : self.subject
    }):
        frappe.db.set_value("Task", self.name, "is_milestone", 1)
        
def validate_parent_task_dates(self):
    if not self.parent_task:
        return
    
    parent = frappe.db.get_value(
        "Task", self.parent_task, ["exp_start_date", "exp_end_date"], as_dict=True
    )
    if not parent:
        return
    
    if parent.exp_start_date and self.exp_start_date and getdate(self.exp_start_date) < getdate(parent.exp_start_date):
        frappe.throw(
            _("Expected Start Date cannot be before the parent task's Expected Start Date ({0})").format(
                frappe.utils.formatdate(parent.exp_start_date)
            )
        )
    
    if parent.exp_end_date and self.exp_end_date and getdate(self.exp_end_date) > getdate(parent.exp_end_date):
        frappe.throw(
            _("Expected End Date cannot be after the parent task's Expected End Date ({0})").format(
                frappe.utils.formatdate(parent.exp_end_date)
            )
        )


def validate_dependent_task_dates(self):
    if self.is_new() or not (self.exp_start_date or self.exp_end_date):
        return

    depends_on_rows = frappe.get_all(
        "Task Depends On",
        filters={"task": self.name, "parenttype": "Task"},
        fields=["parent"],
    )
    if not depends_on_rows:
        return

    parent_task_names = {row.parent for row in depends_on_rows}
    for parent_task_name in parent_task_names:
        parent = frappe.db.get_value(
            "Task", parent_task_name, ["name", "subject", "exp_start_date", "exp_end_date"], as_dict=True
        )
        if not parent:
            continue

        if parent.exp_start_date and self.exp_start_date and getdate(self.exp_start_date) < getdate(parent.exp_start_date):
            frappe.throw(
                _("Expected Start Date cannot be before {0}'s Expected Start Date ({1})").format(
                    frappe.utils.get_link_to_form("Task", parent.name, label=parent.subject),
                    frappe.utils.formatdate(parent.exp_start_date)
                )
            )

        if parent.exp_end_date and self.exp_end_date and getdate(self.exp_end_date) > getdate(parent.exp_end_date):
            frappe.throw(
                _("Expected End Date cannot be after {0}'s Expected End Date ({1})").format(
                    frappe.utils.get_link_to_form("Task", parent.name, label=parent.subject),
                    frappe.utils.formatdate(parent.exp_end_date)
                )
            )


def update_task_details_of_parent_task(self):
    if self.depends_on:
        for row in self.depends_on:
            if not row.custom_employee and row.custom_user:
                if employee := frappe.db.exists("Employee", {"user_id" : row.custom_user}):
                    row.custom_employee = employee 

            if row.task:

                task_doc = frappe.get_doc("Task", row.task)
                task_doc.flags.ignore_permissions = True

                if row.custom_expected_start_date and self.exp_start_date and getdate(row.custom_expected_start_date) < getdate(self.exp_start_date):
                    frappe.throw(
                        _("Row #{0}: Expected Start Date cannot be before this task's Expected Start Date ({1})").format(
                            row.idx, frappe.utils.formatdate(self.exp_start_date)
                        )
                    )

                if row.custom_expected_end_date and self.exp_end_date and getdate(row.custom_expected_end_date) > getdate(self.exp_end_date):
                    frappe.throw(
                        _("Row #{0}: Expected End Date cannot be after this task's Expected End Date ({1})").format(
                            row.idx, frappe.utils.formatdate(self.exp_end_date)
                        )
                    )

                # Update only if values are different
                if row.custom_expected_start_date and task_doc.exp_start_date != row.custom_expected_start_date:
                    task_doc.db_set("exp_start_date", row.custom_expected_start_date, update_modified=False)

                if row.custom_expected_end_date and task_doc.exp_end_date != row.custom_expected_end_date:
                    task_doc.db_set("exp_end_date", row.custom_expected_end_date, update_modified=False)

                if row.custom_expected_time and task_doc.expected_time != row.custom_expected_time:
                    task_doc.db_set("expected_time", row.custom_expected_time, update_modified=False)

                if not task_doc._assign:
                    _assign = []
                else:
                    _assign = eval(task_doc._assign)
                if row.custom_user and row.custom_user not in _assign:
                    if not check_if_assignment(self, user=row.custom_user, task=row.task):
                        add_assignment_as_admin({"doctype": self.doctype, "name": row.task, "assign_to": [row.custom_user]})
                        share_a_task_access(self, task=row.task, user=row.custom_user)
                    task_doc.db_set("custom_assigned_to_responsible_user", row.custom_user, update_modified=False)
                    task_doc.db_set("custom_employee__assign_to_employee_", row.custom_employee, update_modified=False)
                else:
                    if row.custom_user and not task_doc.custom_assigned_to_responsible_user or (row.custom_user and row.custom_user != task_doc.custom_assigned_to_responsible_user):
                        task_doc.db_set("custom_assigned_to_responsible_user", row.custom_user, update_modified=False)
                        if not check_if_assignment(self, user=row.custom_user, task=row.task):
                            add_assignment_as_admin({"doctype": self.doctype, "name": row.task, "assign_to": [row.custom_user]})
                            share_a_task_access(self, task=row.task, user=row.custom_user)
                    if  row.custom_employee and not task_doc.custom_employee__assign_to_employee_ or (row.custom_employee and row.custom_employee != task_doc.custom_employee__assign_to_employee_):
                        task_doc.db_set("custom_employee__assign_to_employee_", row.custom_employee, update_modified=False)

    if self.custom_assigned_to_responsible_user and not check_if_assignment(self):
        add_assignment({"doctype": self.doctype, "name": self.name, "assign_to": [self.custom_assigned_to_responsible_user]})
        share_a_task_access(self)

def add_assignment_as_admin(args):
    current_user = frappe.session.user
    try:
        frappe.set_user("Administrator")
        add_assignment(args)
    finally:
        frappe.set_user(current_user)

def share_a_task_access(self, task=None, user=None):
    if not task:
        task = self.name
    if not user:
        user = self.custom_assigned_to_responsible_user
    frappe.share.add_docshare(
        "Task", task, user, write=1, share=0, flags={"ignore_share_permission": True}
    )

def check_if_assignment(self, user=None, task=None):
    if not task:
        task = self.name
    if not user:
        user = self.custom_assigned_to_responsible_user
    if frappe.db.exists("ToDo", {
        "status" : "Open",
        "allocated_to" : user,
        "reference_type" : "Task",
        "reference_name" : task
    }):
        return True
    else:
        return False



@frappe.whitelist()
def update_time_log(arg):
    args = json.loads(arg)
    if existing_task := frappe.db.exists("Task", {"custom_employee__assign_to_employee_" : args.get("employee"), "working_status" : "Work In Progress"}):
        arg = {
            "task" : existing_task,
            "to_time" : now()
        }
        update_stop_task_log(arg, start_new = True)
    doc = frappe.get_doc("Task", args.get("task"))
    doc.append("unproductive_work_timelogs", {
        "from_time" : args.get("from_time"),
        "activity_type" : args.get('activity_type'),
        "employee" : args.get("employee"),
        "project" : doc.project or args.get("project"),
        "task" : args.get("task")
    })
    if not doc.custom_employee__assign_to_employee_:
        doc.custom_employee__assign_to_employee_ = args.get("employee")
    doc.flags.ignore_permissions=True
    doc.working_status = "Work In Progress"
    doc.save()
    return True

@frappe.whitelist()
def update_stop_task_log(arg, start_new=False):
    try:
        args = json.loads(arg)
    except:
        args = arg
    doc = frappe.get_doc("Task", args.get("task"))
    row = doc.unproductive_work_timelogs[-1]
    doc.unproductive_work_timelogs[-1].to_time = args.get("to_time")
    project = doc.project or row.get("project")
    if not row.get("to_time") or row.get("to_time") == '':
        row.update({
            "to_time" : args.get("to_time")
        })

    doc.flags.ignore_permissions = True
    doc.save()

    log_date = getdate(row.get("from_time"))
    month_start = log_date.replace(day=1)
    month_end = get_last_day(log_date)

    timesheet = frappe.db.get_value("Timesheet", {
                    "employee" : doc.custom_employee__assign_to_employee_,
                    "parent_project" : project ,
                    "docstatus" :  0,
                    "start_date" : ["between", [month_start, month_end]]
                } ,"name")
    if timesheet:
        timesheet_doc = frappe.get_doc("Timesheet", timesheet)
        timesheet_doc.flags.ignore_permissions = True
        # Check if an open (not yet stopped) time log for this task already exists to avoid self-overlap
        existing_log = next(
            (tl for tl in timesheet_doc.time_logs if tl.task == args.get("task") and not tl.to_time),
            None
        )
        if existing_log:
            existing_log.to_time = row.get("to_time")
        else:
            timesheet_doc.append("time_logs", {
                "activity_type" : row.get("activity_type"),
                "from_time" : row.get("from_time"),
                "to_time" : row.get("to_time"),
                "employee" : row.get("employee"),
                "project" : project,
                "task" : args.get("task")
            })
        timesheet_doc.flags.ignore_permissions=True
        timesheet_doc.save()
    else:
        new_timesheet_doc = frappe.get_doc({
            "doctype" : "Timesheet",
            "parent_project" : project,
            "company" : doc.company,
            "employee" : row.get("employee"),
            "start_date" : month_start,
            "time_logs" : [
                {
                    "activity_type" : row.get("activity_type"),
                    "from_time" : row.get("from_time"),
                    "to_time" : row.get("to_time"),
                    "employee" : row.get("employee"),
                    "project" : project,
                    "task" : args.get("task")
                }
            ]
        })
        new_timesheet_doc.flags.ignore_permissions = True
        new_timesheet_doc.insert()
    frappe.db.set_value("Task",args.get("task"), "working_status", "On Hold")
    return True

# Scheduler : Stop Timer after every 2 hours
def update_task_timer():
    task_list = frappe.db.get_list("Task", {"working_status" : 'Work In Progress'})
    permissable_hours = frappe.db.get_single_value("Projects Settings", "task_cut_of_time")
    for row in task_list:
        doc = frappe.get_doc("Task", row.name)

        if not doc.unproductive_work_timelogs:
            continue

        # Find the active unproductive log: to_time is empty and from_time is set
        active_log = None
        for tl in doc.unproductive_work_timelogs:
            if not tl.to_time and tl.from_time:
                active_log = tl

        if not active_log:
            continue

        from_time = get_datetime(active_log.from_time)
        current_time = get_datetime()
        diff_hours = (current_time - from_time).total_seconds() / 3600

        shift_end_reached = False
        if doc.custom_employee__assign_to_employee_:
            shift_end_reached = has_employee_shift_ended(doc.custom_employee__assign_to_employee_, current_time)

        if diff_hours >= permissable_hours or shift_end_reached:
            arg = {
                "task" : row.name,
                "to_time" : now()
            }
            update_stop_task_log(arg, start_new=True)
            if doc.custom_employee__assign_to_employee_:
                send_timer_stopper_notification(doc, permissable_hours)
            frappe.db.commit()


def has_employee_shift_ended(employee, current_time):
    default_shift = frappe.db.get_value("Employee", employee, "default_shift")
    if not default_shift:
        return False

    end_time = frappe.db.get_value("Shift Type", default_shift, "end_time")
    if not end_time:
        return False

    shift_end_datetime = datetime.combine(current_time.date(), (datetime.min + end_time).time())
    return current_time >= shift_end_datetime

def send_timer_stopper_notification(doc, permissible_hours):
    employee_name = frappe.db.get_value(
        "Employee",
        doc.custom_employee__assign_to_employee_,
        "employee_name"
    )

    user_id = frappe.db.get_value(
        "Employee",
        doc.custom_employee__assign_to_employee_,
        "user_id"
    )

    if not user_id:
        return

    task_url = f"{frappe.utils.get_url()}/app/task/{doc.name}"

    message = f"""
        <div style="font-family: Arial, Helvetica, sans-serif; color:#333; line-height:1.6;">
            <p>Hi <strong>{employee_name}</strong>,</p>

            <p style="font-size:14px;">
                You have exceeded the permissible working limit of 
                <strong>{permissible_hours} hours</strong>.
                If you are still working, please open the task below and restart the timer.
            </p>

            <div style="margin:18px 0; padding:12px 16px; background:#f8f9fa; border-left:4px solid #4b7bec;">
                <p style="margin:0; font-size:14px;">
                    <strong>Task:</strong>{get_link_to_form("Task", doc.name)}
                </p>
            </div>

            <p style="font-size:14px;">
                Thank you,<br>
                <span style="color:#555;">Regards</span>
            </p>

            <hr style="border:none; border-top:1px solid #e0e0e0; margin-top:30px;">

            <p style="text-align:center; font-size:12px; color:#888;">
                This is a system-generated email. Please do not reply.
            </p>
        </div>
    """

    subject = "Action Required: Please Restart Your Task Timer"

    frappe.sendmail(
        recipients=[user_id],
        subject=subject,
        message=message
    )


@frappe.whitelist()
def get_employee_id(user):
    if employee := frappe.db.exists("Employee", {"user_id" : user}):
        return employee
    else:
        None


## custom method to updated status of dependent task in parent task child table
def update_parent_task_dependency_status(doc, method=None):
    current_task = doc.name
    current_status = doc.status

    parent_tasks = frappe.get_all(
        "Task Depends On",
        filters={"task": current_task},
        fields=["parent"]
    )

    for row in parent_tasks:
        parent_task = frappe.get_doc("Task", row.parent)
        updated = False

        for dep in parent_task.depends_on:
            if dep.task == current_task:
                if dep.custom_status != current_status:
                    dep.custom_status = current_status
                    updated = True

        if updated:
            parent_task.flags.ignore_permissions = True
            parent_task.save()



def get_extra_days(exp_end_date, act_end_date):
    """
    Calculate extra days taken compared to expected duration
    using Frappe date utilities.
    """

    # Convert to date objects
    exp_end_date = getdate(exp_end_date)
    act_end_date = getdate(act_end_date)

    # Duration calculations
    expected_days = date_diff(act_end_date ,exp_end_date)
    return max(expected_days, 0)


def update_department(self):
    if not self.department:
        self.department = frappe.db.get_value("Employee", self.custom_employee__assign_to_employee_, "department")
    

# @frappe.whitelist()
# @frappe.validate_and_sanitize_search_inputs
# def get_activity_type(doctype, txt, searchfield, start, page_len, filters):
#     conditions = []
#     values = {}

#     # Department filter
#     if filters.get("department"):
#         conditions.append("pt.department = %(department)s")
#         values["department"] = filters.get("department")

#     # Unproductive work filter
#     if filters.get("custom_unproductive_work") is not None:
#         conditions.append("at.custom_unproductive_work = %(custom_unproductive_work)s")
#         values["custom_unproductive_work"] = filters.get("custom_unproductive_work")
#     else:
#         conditions.append("at.custom_unproductive_work = 0")

#     # Search text
#     if txt:
#         conditions.append("at.name LIKE %(txt)s")
#         values["txt"] = f"%{txt}%"

#     # Employee-based department (only if department not already set)
#     if not values.get("department") and filters.get("employees"):
#         employee = filters.get("employees")
#         if employee:
#             department = frappe.db.get_value(
#                 "Employee", employee, "department"
#             )
#             if department:
#                 conditions.append("pt.department = %(department)s")
#                 values["department"] = department

#     # Job Card Type condition (FIXED LOGIC)
#     if filters.get("custom_job_card_type"):
#         conditions.append(
#             "(at.custom_job_card_type IS NOT NULL OR at.custom_job_card_type != '')"
#         )
#     else:
#         conditions.append(
#             "(at.custom_job_card_type IS NULL OR at.custom_job_card_type = '')"
#         )

#     condition_sql = ""
#     if conditions:
#         condition_sql = " AND " + " AND ".join(conditions)

#     data = frappe.db.sql(
#         f"""
#         SELECT at.name
#         FROM `tabActivity Type` at
#         LEFT JOIN `tabParent Activity` pt
#             ON pt.name = at.parent_activity_type
#         WHERE 1=1
#         {condition_sql}
#         LIMIT %(start)s, %(page_len)s
#         """,
#         {
#             **values,
#             "start": start,
#             "page_len": page_len
#         }
#     )
#     return data


def remove_assignment_while_changing(self):
    if self.is_new():
        return
    old_doc = self.get_doc_before_save()
    if old_doc and old_doc.custom_assigned_to_responsible_user != self.custom_assigned_to_responsible_user:
        remove_assignments(self, self.doctype, self.name, old_doc.custom_assigned_to_responsible_user, ignore_permissions=True)

def remove_assignments(self, doctype, name, assignee, ignore_permissions=False):
    if not assignee:
        return

    set_status(
        doctype,
        name,
        todo=None,
        assign_to=assignee,
        status="Cancelled",
        ignore_permissions=ignore_permissions,
    )
    frappe.share.add("Task", self.name, assignee, read=0, write=0, share=0)


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return ""

    return f"""(`tabTask`.owner = {frappe.db.escape(user)}
        OR `tabTask`._assign LIKE {frappe.db.escape('%' + user + '%')})"""


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_employee_wise_activity(doctype, txt, searchfield, start, page_len, filters):
    conditions = []
    values = {
        "start": start,
        "page_len": page_len,
    }

    employee = filters.get("employee")
    department = None

    if employee:
        department = frappe.db.get_value(
            "Employee", employee, "custom_department_for_timesheet"
        )

    if department:
        conditions.append("at.custom_department_for_timesheet = %(department)s")
        values["department"] = department
    else:
        # No employee selected, or employee has no department set ->
        # show nothing rather than leaking activity types from other departments
        conditions.append("1=0")

    if txt:
        conditions.append("at.name LIKE %(txt)s")
        values["txt"] = f"%{txt}%"

    condition_sql = ""
    if conditions:
        condition_sql = " AND " + " AND ".join(conditions)

    data = frappe.db.sql(
        f"""
        SELECT at.name
        FROM `tabActivity Type` at
        WHERE 1=1
        {condition_sql}
        LIMIT %(start)s, %(page_len)s
        """,
        values,
    )
    return data

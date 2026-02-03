import frappe
from frappe.utils import today, get_datetime, now_datetime, time_diff_in_seconds, now
from harro.harro.docevents.task import update_stop_task_log
from harro.harro.docevents.employee_checkin import update_unproductive_log_employee_wise, make_time_log
from frappe.utils import get_url_to_form, get_link_to_form
from harro.harro.docevents.job_card import update_unproductive_log


@frappe.whitelist()
def get_supplier_list(doctype, txt, searchfield, start, page_len, filters):
    filters = frappe._dict(filters)
    rfq_doc = frappe.get_doc("Request for Quotation", filters.get("name"))

    sq_supplier_list = frappe.db.sql(f"""
                                     Select sq.supplier
                                     From `tabSupplier Quotation` as sq
                                     Left Join `tabSupplier Quotation Item` as sqi ON sqi.parent = sq.name
                                     Where sq.docstatus < 2 and sqi.request_for_quotation = '{rfq_doc.name}'
                                """, as_dict=1)
    
    sq_supplier = [
        row.supplier for row in sq_supplier_list
    ]
    
    rfq_supplier_list = [
        row.supplier for row in rfq_doc.suppliers
    ]

    final_supplier_list = tuple([(s,) for s in rfq_supplier_list if s not in sq_supplier])

    return final_supplier_list



@frappe.whitelist()
def get_open_tasks_for_user():
    user = frappe.session.user

    # find task assigned to currently logged in user
    todos = frappe.db.get_all(
        "ToDo",
        filters = {
            "reference_type": "Task",
            "allocated_to": user,
            "status": "Open"
        },
        pluck = "reference_name"
    )

    if not todos:
        return {
            "value": 0,
            "fieldtype": "Int"
        }
    
    # count only valid tasks that are not completed/cancelled/template
    count = frappe.db.count(
        "Task",
        filters={
            "name": ["in",todos],
            "status": ["not in", ["Completed","Cancelled","Template"]]
        }
    )

    return {
        "value": count,
        "fieldtype": "Int",
        "route": ["List", "Task"],
        "route_options": {
            "_assign": ["like", f"%{user}%"],
            "status": ["not in", ["Completed","Cancelled","Template"]]
        }
    }



def update_the_task_timer_based_on_shift_end():

    try:
        employees = frappe.get_all(
            "Employee",
            filters={"default_shift": ["!=", ""]},
            fields=["name", "default_shift"]
        )
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Shift End Task Timer: Error fetching employees"
        )
        return

    if not employees:
        return

    for employee in employees:
        try:
            shift_end_time = frappe.db.get_value(
                "Shift Type",
                employee.default_shift,
                "end_time"
            )

            if not shift_end_time:
                continue

            shift_end_dt = get_datetime(f"{today()} {shift_end_time}")
            current_dt = now_datetime()
            diff_minutes = time_diff_in_seconds(shift_end_dt, current_dt) / 60

            # Only process tasks within -5 to 0 min of shift end
            if not (-5 <= diff_minutes <= 0):
                continue

            task_list = frappe.db.sql(
                """
                SELECT 
                    t.name AS task_name,
                    td.name AS timesheet_detail
                FROM `tabTask` t
                LEFT JOIN `tabTimesheet Detail` td 
                    ON td.parent = t.name
                WHERE 
                    t.status != 'Cancelled' AND
                    t.working_status = 'Work In Progress'
                    AND t.custom_employee__assign_to_employee_ = %(employee)s
                    AND (td.to_time IS NULL OR td.to_time = '')
                    AND td.creation < %(now)s
                """,
                {
                    "employee": employee.name,
                    "now": shift_end_dt
                },
                as_dict=True,
            )

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Shift End Task Timer: Error pre-processing employee {employee.name}"
            )
            continue

        for row in task_list:
            try:
                arg = {
                    "task": row.task_name,
                    "to_time": now()
                }

                # stop timer
                update_stop_task_log(arg, start_new=True)

                # --- email notification ---
                try:
                    user = frappe.db.get_value(
                        "Employee",
                        employee.name,
                        ["user_id"],
                        as_dict=True
                    )

                    if not user or not user.user_id:
                        continue

                    # get email of the user
                    recipient_email = user.user_id

                    if not recipient_email:
                        continue

                    # task link
                    task_link = get_url_to_form("Task", row.task_name)

                    frappe.sendmail(
                        recipients=[recipient_email],
                        subject="Task Timer Stopped Due to Shift End",
                        message=f"""
                            <div style="font-family: Arial, Helvetica, sans-serif; color:#333; line-height:1.6;">
                                
                                <p>Hi,</p>

                                <p style="font-size:14px;">
                                    Your task timer has been <strong>automatically stopped</strong> because your
                                    working shift has ended.
                                </p>

                                <div style="margin:18px 0; padding:12px 16px; background:#f8f9fa; border-left:4px solid #4b7bec;">
                                    <p style="margin:0; font-size:14px;">
                                        <strong>Task:</strong> {get_link_to_form("Task",row.task_name)}
                                    </p>
                                </div>

                                <p style="font-size:14px;">
                                    If you are still working on this task, please update the Timesheet or restart the task timer.
                                </p>

                                <p style="margin-top:22px;">
                                    <a href="{task_link}" 
                                        style="background:#1a73e8; color:#fff; padding:10px 16px; 
                                            text-decoration:none; border-radius:4px; font-size:14px;">
                                        Open Task
                                    </a>
                                </p>

                                <p style="font-size:14px;">Thanks,</p>

                                <hr style="border:none; border-top:1px solid #e0e0e0; margin-top:28px;">

                                <p style="text-align:center; font-size:12px; color:#888;">
                                    This is a system-generated email. Please do not reply.
                                </p>

                            </div>
                        """
                    )


                except Exception:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f"Shift End Task Timer: Error emailing for task {row.task_name} employee {employee.name}"
                    )

            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Shift End Task Timer: Error updating task {row.task_name} for employee {employee.name}"
                )



def update_the_job_card_timer_based_on_shift_end():

    try:
        employees = frappe.get_all(
            "Employee",
            filters={"default_shift": ["!=", ""]},
            fields=["name", "default_shift"]
        )
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Shift End Job Card Timer: Error fetching employees"
        )
        return

    if not employees:
        return

    for emp in employees:
        try:
            shift_end_time = frappe.db.get_value(
                "Shift Type",
                emp.default_shift,
                "end_time"
            )

            if not shift_end_time:
                continue

            shift_end_dt = get_datetime(f"{today()} {shift_end_time}")
            current_dt = now_datetime()
            diff_minutes = time_diff_in_seconds(shift_end_dt, current_dt) / 60

            if not (-5 <= diff_minutes <= 0):
                continue

            job_card_list = frappe.db.sql(
                """
                SELECT 
                    jc.name AS job_card,
                    jc.project,
                    jct.name AS timesheet_detail
                FROM `tabJob Card` jc
                LEFT JOIN `tabJob Card Time Log` jct
                    ON jct.parent = jc.name
                WHERE 
                    jc.status = 'Work In Progress'
                    AND jct.employee = %(employee)s
                    AND (jct.to_time IS NULL OR jct.to_time = '')
                    AND jct.creation < %(now)s
                """,
                {
                    "employee": emp.name,
                    "now": shift_end_dt
                },
                as_dict=True,
            )

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Shift End Job Card Timer: Error pre-processing employee {emp.name}"
            )
            continue

        for row in job_card_list:
            try:
                # Log unproductive entry
                args = {
                    "activity_type": "Shift End",
                    "from_time": now_datetime(),
                    "project": row.project,
                }
                update_unproductive_log_employee_wise(args, row.job_card, emp.name)

                # Stop time log
                args = {
                    'job_card_id': row.job_card,
                    "complete_time": now(),
                    "status": "On Hold",
                    "completed_qty": 0,
                }

                make_time_log(args)

                try:
                    # get user_id from employee
                    user = frappe.db.get_value(
                        "Employee",
                        emp.name,
                        ["user_id"],
                        as_dict=True
                    )

                    if not user or not user.user_id:
                        continue

                    # get email from user
                    recipient_email = user.user_id

                    if not recipient_email:
                        continue

                    # Job Card link
                    job_card_link = get_url_to_form("Job Card", row.job_card)

                    frappe.sendmail(
                        recipients=[recipient_email],
                        subject="Job Card Timer Stopped Due to Shift End",
                        message=f"""
                            <p>Hi,</p>

                            <p>
                                Your Job Card timer has been stopped automatically 
                                because your shift has ended.
                            </p>

                            <p>
                                <b>Job Card:</b> 
                                <a href="{job_card_link}">{row.job_card}</a>
                            </p>

                            <p>
                                If you are still working on this job,
                                please update the Time Log or restart the timer.
                            </p>

                            <p>Thanks</p>
                        """
                    )

                except Exception:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f"Shift End Job Card Timer: Error emailing for Job Card {row.job_card} employee {emp.name}"
                    )

            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Shift End Job Card Timer: Error updating Job Card {row.job_card} for employee {emp.name}"
                )



def stop_timer_for_jobcard_every_two_hours():
    jobcard_list = frappe.db.get_all("Job Card", filters={"status" : 'Work In Progress'}, fields=["name", "project"])

    for row in jobcard_list:
        doc = frappe.get_doc("Job Card", row.name)

        if not doc.time_logs:
            continue

        from_time = doc.time_logs[-1].from_time
        current_time = get_datetime()
        diff_hours = (current_time - from_time).total_seconds() / 3600
        employee = doc.time_logs[-1].employee

        permissable_hours = frappe.db.get_single_value(
            "Projects Settings",
            "job_card_cut_of_time"
        )

        if diff_hours >= permissable_hours:

            # Log unproductive entry

            args = {
                "activity_type": "Reached Permissable Work Hours",
                "from_time": now_datetime(),
                "project": row.get("project"),
            }
            update_unproductive_log(args, row.name)

            # stop time log
            args = {
                'job_card_id': row.name,
                "complete_time": get_datetime(),
                "status": "On Hold",
                "completed_qty": 0,
            }
            make_time_log(args)

            # ============== EMAIL NOTIFICATION =================
            try:
            
                if not employee:
                    continue

                # get user_id
                user = frappe.db.get_value(
                    "Employee",
                    employee,
                    ["user_id"],
                    as_dict=True
                )

                if not user or not user.user_id:
                    continue

                # get email id
                recipient_email = user.user_id

                if not recipient_email:
                    continue

                # job card link
                job_card_link = get_url_to_form("Job Card", row.name)

                frappe.sendmail(
                    recipients=[recipient_email],
                    subject="Job Card Timer Stopped — Cut-off Limit Reached",
                    message=f"""
                        <p>Hi,</p>

                        <p>
                            Your Job Card timer has been stopped automatically because 
                            the configured cut-off time of <b>{permissable_hours} hour(s)</b> 
                            has been reached.
                        </p>

                        <p>
                            <b>Job Card:</b>
                            <a href="{job_card_link}">{row.name}</a>
                        </p>

                        <p>
                            If you are still working on this job,
                            please update the Time Log or restart the timer.
                        </p>

                        <p>Thanks,<br>System</p>
                    """
                )

            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Job Card Cut-off Timer: Error sending email for Job Card {row.name}"
                )

            
from harro.harro.docevents.bom_creator import make_fieldname


def get_item_master_data_for_print(item, manufacturer_part_no=None):
    uniq_part_no = []
    desc_data_list = []

    doc = frappe.get_doc("Item", item)

    for_description = [
        "Artikel Bez1",
        "Artikel Bez2",
        "Artikel Bez3",
        "Artikel Bez4",
    ]
    fieldname_list = []
    for row in for_description:
        fieldname = make_fieldname(row)
        fieldname_list.append(fieldname)
    for l in fieldname_list:
        desc_data_list.append(doc.get(l))
    if manufacturer_part_no not in desc_data_list:
        uniq_part_no.append(manufacturer_part_no)
    if doc.cbestellnummer not in desc_data_list:
        uniq_part_no.append(doc.cbestellnummer)
    if doc.cherstellerbez not in desc_data_list:
        uniq_part_no.append(doc.cherstellerbez)

    uniq_part_no = list(set(uniq_part_no))

    return uniq_part_no

## api to update raw material in production plan
from frappe.utils import flt
from erpnext.manufacturing.report.bom_stock_report.bom_stock_report import get_bom_stock

@frappe.whitelist()
def reduce_raw_material_qty(production_plan, items):
    doc = frappe.get_doc("Production Plan", production_plan)
    if isinstance(items, str):
        items = frappe.parse_json(items)

    # extract selected item codes from Table MultiSelect
    selected_items = [d.get("item_code") for d in items if d.get("item_code")]
    if not selected_items:
        frappe.throw("No items selected")

    # map mr items by item_code for fast lookup
    mr_items_map = {}
    for row in doc.mr_items:
        mr_items_map.setdefault(row.item_code, []).append(row)

    for sub in doc.sub_assembly_items:
        if sub.production_item not in selected_items:
            continue
        fg_warehouse = sub.fg_warehouse
        if not fg_warehouse:
            fg_warehouse = doc.sub_assembly_warehouse
        if not sub.bom_no or not sub.fg_warehouse:
            frappe.throw(
                f"BOM or FG Warehouse missing for <b>{sub.production_item}</b>"
            )

        filters = frappe._dict({
            "bom": sub.bom_no,
            "warehouse": sub.fg_warehouse,
            "qty_to_produce": sub.qty
        })

        data = get_bom_stock(filters) or []

        for row in data:

            item_code = row[0]
            bom_qty = flt(row[5])

            if not item_code or item_code not in mr_items_map:
                continue

            for mr_row in list(mr_items_map[item_code]):
                current_qty = flt(mr_row.quantity)
                new_qty = current_qty - bom_qty

                if new_qty < 0:
                    frappe.throw(
                        f"""
                        Insufficient raw material for item <b>{item_code}</b><br>
                        Required: {bom_qty}<br>
                        Available: {current_qty}
                        """
                    )

                if new_qty == 0:
                    doc.remove(mr_row)
                else:
                    mr_row.quantity = new_qty

    doc.save(ignore_permissions=True)

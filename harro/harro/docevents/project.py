import frappe
from frappe.utils import flt, get_fullname


def validate(self, method):
    # Keep existing manufacturing hours calculation
    self.planned_manufacturing_hours = round(
        flt(self.planned_mechanical_assembly)
        + flt(self.planned_electrical_assembly),
        2,
    )

    # Trigger email when workflow state moves to "Approved"
    # try:
    #     send_project_approval_email_if_required(self)
    # except Exception as e:
    #     # Never block save if email fails; just log it
    #     frappe.log_error(
    #         message=frappe.get_traceback(),
    #         title=f"Project approval email failed for {getattr(self, 'name', '')}: {e}",
    #     )


def send_project_approval_email_if_required(doc):
    """Send welcome email to project stakeholders when workflow_state becomes 'Approved'."""
    # Current state on the in-memory document
    current_state = getattr(doc, "workflow_state", None)

    # Only continue if current state is Approved
    if current_state != "Approved":
        return

    # Get previous workflow_state from DB to ensure this is a transition
    previous_state = None
    if not doc.is_new():
        previous_state = frappe.db.get_value("Project", doc.name, "workflow_state")

    # If it was already Approved before, do nothing (avoid duplicate emails)
    if previous_state == "Approved":
        return

    # Collect stakeholder emails from Project User child table (fields: user, custom_employee)
    project_users = frappe.get_all(
        "Project User",
        filters={"parent": doc.name, "parenttype": "Project"},
        fields=["user"],
    )

    user_ids = [row.user for row in project_users if row.get("user")]
    if not user_ids:
        return

    recipient_emails = frappe.get_all(
        "User",
        filters={"name": ["in", user_ids], "enabled": 1},
        pluck="email",
    )
    recipient_emails = [e for e in recipient_emails if e]

    if not recipient_emails:
        return

    # Build dynamic values from Project
    ba_number = getattr(doc, "custom_ba_number", None) or getattr(doc, "name", "")
    # Try both standard and custom naming for machine type / BA type to be safe
    machine_type = (
        getattr(doc, "machine_type", None)
        or getattr(doc, "custom_machine_type", None)
        or ""
    )
    ba_type = (
        getattr(doc, "ba_type", None)
        or getattr(doc, "custom_ba_type", None)
        or ""
    )

    # Approver (current session user)
    approver_user = frappe.session.user
    approver_name = get_fullname(approver_user) if approver_user else ""

    subject = f"Welcome to Our New Project (BA Number: {ba_number})"

    # Simple text/HTML hybrid body
    message = f"""
Hi All,<br><br>
I am delighted to welcome you to our new project!<br><br>
<b>Project Details:</b><br>
BA Number: {ba_number}<br>
Machine Type: {machine_type or 'N/A'}<br>
BA Type: {ba_type or 'N/A'}<br><br>
In the coming days, we will be holding our project stakeholder meeting, where we will discuss the timelines for each task. If you have any questions or ideas, please don’t hesitate to reach out.<br><br>
Looking forward to a great collaboration!<br><br>
Best regards,<br>
{approver_name or approver_user}
"""

    frappe.sendmail(
        recipients=recipient_emails,
        subject=subject,
        message=message,
        reference_doctype="Project",
        reference_name=doc.name,
    )

# This function is calculating a job card hours
def calculate_productive_working_hours(project):
    if not project:
        return

    job_cards = frappe.db.sql(f"""
                              
                                Select jc.name, jct.time_in_mins, jct.activity_type, at.custom_job_card_type as job_operation
                                From `tabJob Card` as jc
                                Left Join `tabJob Card Time Log` as jct ON jct.parent = jc.name
                                Left Join `tabActivity Type` as at ON at.name = jct.activity_type
                                Where jc.docstatus < 2 and jc.project = '{project}'
                              
                              """, as_dict=1)
    


    # Dictionary to hold operation-wise total minutes
    if not job_cards:
        frappe.db.set_value("Project", project, "actual_mechanical_assembly", 0)
        frappe.db.set_value("Project", project, "actual_electrical_assembly", 0)
        frappe.db.set_value("Project", project, "actual_manufacturing_hours", 0)
        return

    operation_wise_time = {}

    for jc in job_cards:
        operation = jc.job_operation or "Unknown"
        total_time_in_mins = flt(jc.time_in_mins) or 0

        # Sum total time for each operation
        operation_wise_time[operation] = flt(operation_wise_time.get(operation, 0)) + total_time_in_mins
    
    current_actule_manufacturing_hours = frappe.db.get_value("Project", project, "actual_manufacturing_hours") or 0

    if operation_wise_time.get("Mechanical"):
        frappe.db.set_value("Project", project, "actual_mechanical_assembly", round(operation_wise_time.get("Mechanical")/60, 2))

    if operation_wise_time.get("Electrical"):
        frappe.db.set_value("Project", project, "actual_electrical_assembly", round(operation_wise_time.get("Electrical")/60, 2))
    
    actual_mechanical_assembly = flt(operation_wise_time.get("Mechanical")) or 0
    actual_electrical_assembly = flt(operation_wise_time.get("Electrical")) or 0

    current_actule_manufacturing_hours = round(flt(actual_mechanical_assembly) + flt(actual_electrical_assembly) + flt(current_actule_manufacturing_hours), 2)

    frappe.db.set_value("Project", project, "actual_manufacturing_hours", round(current_actule_manufacturing_hours/60, 2))
    


    

import frappe

@frappe.whitelist()
def get_effort_data(project):
    """Return planned and actual hours for all 3 categories."""
    fields = [
        "planned_manufacturing_hours",
        "actual_manufacturing_hours",
        "planned_mechanical_assembly",
        "actual_mechanical_assembly",
        "planned_electrical_assembly",
        "actual_electrical_assembly",
    ]

    data = frappe.db.get_value("Project", project, fields, as_dict=True) or {}

    return {
        "planned_manufacturing_hours": data.get("planned_manufacturing_hours", 0),
        "actual_manufacturing_hours": data.get("actual_manufacturing_hours", 0),
        "planned_mechanical_assembly": data.get("planned_mechanical_assembly", 0),
        "actual_mechanical_assembly": data.get("actual_mechanical_assembly", 0),
        "planned_electrical_assembly": data.get("planned_electrical_assembly", 0),
        "actual_electrical_assembly": data.get("actual_electrical_assembly", 0),
    }



def calculate_timesheet_hours(project):
    timesheet_details = frappe.db.sql(f"""
                                    
                                    Select sum(td.hours) as hours , td.activity_type
                                    From `tabTimesheet` as t
                                    Left Join `tabTimesheet Detail` as td ON td.parent = t.name
                                    Left Join `tabActivity Type` as at ON at.name = td.activity_type
                                    Where t.parent_project = '{project}' and t.docstatus = 1 
                                    Group By td.activity_type

                                        """, as_dict=True)
        
    field_to_update = frappe.db.get_all("Activity Type" , fields = ['name', 'custom_update_to_project_field'], filters={'custom_update_to_project_field' : ["!=", ''], "disabled" : 0})

    field_mapping = {}
    for row in field_to_update:
        field_mapping.update({
            row.name : row.custom_update_to_project_field
        })
    if timesheet_details:
        for row in timesheet_details:
            if field_mapping.get(row.activity_type):
                frappe.db.set_value("Project", project, field_mapping.get(row.activity_type), round(row.hours, 2))
    else:
        for row in field_to_update:
            if field_mapping.get(row.name):
                frappe.db.set_value("Project", project, field_mapping.get(row.name), 0)

@frappe.whitelist()
def get_timesheet_working_hours(name, unproductive):
    doc = frappe.get_doc("Project", name)
    fielddetails = frappe.db.get_all(
                                     "Activity Type", 
                                     fields=["custom_update_to_project_field", "custom_planned_hours_field_name", "name", "parent_activity_type"], 
                                     filters={"custom_unproductive_work" : unproductive, "disabled" : 0}, 
                                     group_by = "parent_activity_type"
                                    )
    dataset = []
    count = 0 
    for row in fielddetails:
        if row.get("custom_update_to_project_field") and row.get("custom_planned_hours_field_name"):
            dataset.append({
                "label": row.get("parent_activity_type") or row.get("name"),
                "actual": doc.get(row.get("custom_update_to_project_field")),
                "planned": doc.get(row.get("custom_planned_hours_field_name")),
                "index": count
            })
            count += 1
    return dataset

@frappe.whitelist() 
def get_activity(unproductive=0):
    fielddetails = frappe.db.get_all(
                                     "Activity Type", 
                                     fields=["custom_update_to_project_field", "custom_planned_hours_field_name", "name", "parent_activity_type"], 
                                     filters={"custom_unproductive_work" : unproductive, "disabled" : 0}, 
                                     group_by = "parent_activity_type"
                                    )
    
    activity_list = []
    for row in fielddetails:
        if row.get("custom_update_to_project_field") and row.get("custom_planned_hours_field_name"):
            activity_list.append(row.get("parent_activity_type") or row.get("name"))
        
    return activity_list


## custom function for employee chart
# @frappe.whitelist()
# def get_project_hierarchy(project):
#     project_employees = frappe.get_all(
#         "Project User",   
#         filters={"parent": project},
#         pluck="custom_employee"
#     )

#     if not project_employees:
#         return []
#     employees = frappe.get_all(
#         "Employee",
#         filters={
#             "name": ["in", project_employees],
#             "status": "Active"
#         },
#         fields=[
#             "name as id",
#             "employee_name as name",
#             "reports_to",
#             "designation as title",
#             "image",
#             "lft",
#             "rgt"
#         ],
#         order_by="employee_name"
#     )

#     for emp in employees:
#         emp.connections = sum(
#             1 for e in employees if e.get("reports_to") == emp.id
#         )
#         emp.expandable = bool(emp.connections)
#     frappe.log_error(message=frappe.as_json(employees), title="employees")
#     return employees



@frappe.whitelist()
def get_project_hierarchy(project, parent=None):
    """
    Get employee hierarchy for a project
    - If parent is None: returns root nodes (employees without a manager in the project)
    - If parent is provided: returns direct reports of that parent
    """
    project_employees = frappe.get_all(
        "Project User",   
        filters={"parent": project},
        pluck="custom_employee"
    )

    if not project_employees:
        return []
    
    # Build filters based on parent parameter
    filters = {
        "name": ["in", project_employees],
        "status": "Active"
    }
    
    if parent:
        # Get direct reports of this parent
        filters["reports_to"] = parent
    else:
        # Get root nodes: employees with no reports_to OR reports_to not in project
        filters["reports_to"] = ["is", "set"]
    
    employees = frappe.get_all(
        "Employee",
        filters=filters,
        fields=[
            "name as id",
            "employee_name as name",
            "reports_to",
            "designation as title",
            "image"
        ],
        order_by="employee_name"
    )
    
    # For root nodes, we need to filter out those whose manager is also in the project
    if not parent:
        root_employees = []
        for emp in employees:
            if not emp.reports_to or emp.reports_to not in project_employees:
                root_employees.append(emp)
        employees = root_employees
    
    # Get count of direct reports for each employee
    for emp in employees:
        # Count how many employees report to this person within the project
        direct_reports = frappe.db.count(
            "Employee",
            filters={
                "reports_to": emp.id,
                "name": ["in", project_employees],
                "status": "Active"
            },
        )
        emp.connections = direct_reports
        emp.expandable = direct_reports > 0
    
    frappe.log_error(message=frappe.as_json(employees), title=f"Project hierarchy for {project}")
    return employees

@frappe.whitelist()
def get_all_project_nodes(project):
    """
    Get all nodes in the project hierarchy for Expand All functionality
    Returns a list of [parent, [children]] pairs
    """
    project_employees = frappe.get_all(
        "Project User",   
        filters={"parent": project},
        pluck="custom_employee"
    )

    if not project_employees:
        return []
    
    # Get all active employees in the project
    all_employees = frappe.get_all(
        "Employee",
        filters={
            "name": ["in", project_employees],
            "status": "Active"
        },
        fields=[
            "name as id",
            "employee_name as name",
            "reports_to",
            "designation as title",
            "image"
        ]
    )
    
    # Build a mapping of manager -> direct reports
    manager_map = {}
    for emp in all_employees:
        if emp.reports_to:
            manager_map.setdefault(emp.reports_to, []).append(emp)
    
    # Create result in the format expected by the frontend
    result = []
    for emp in all_employees:
        if emp.id in manager_map:  # This employee has direct reports
            children = manager_map[emp.id]
            
            # Format parent
            parent_data = {
                "id": emp.id,
                "name": emp.name,
                "title": emp.title,
                "image": emp.image,
                "connections": len(children),
                "expandable": True
            }
            
            # Format children
            children_data = []
            for child in children:
                child_data = {
                    "id": child.id,
                    "name": child.name,
                    "title": child.title,
                    "image": child.image,
                    "connections": len(manager_map.get(child.id, [])),
                    "expandable": child.id in manager_map
                }
                children_data.append(child_data)
            
            result.append([parent_data, children_data])
    
    return result


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator" or set(frappe.get_roles(user)) & {"System Manager", "Project Manager"}:
        return ""

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")

    return f"""(`tabProject`.owner = {frappe.db.escape(user)}
        OR EXISTS (
            SELECT 1 FROM `tabProject User` pu
            WHERE pu.parent = `tabProject`.name
                AND pu.parenttype = 'Project'
                AND (pu.user = {frappe.db.escape(user)}
                    {f"OR pu.custom_employee = {frappe.db.escape(employee)}" if employee else ""})
        ))"""


def set_custom_title(doc, method):
    custom_ba_number = doc.custom_ba_number or ""
    project_name = doc.project_name or ""

    if custom_ba_number or project_name:
        if custom_ba_number and project_name:
            doc.custom_title = f"{custom_ba_number} - {project_name}"
        else:
            doc.custom_title = custom_ba_number or project_name
    else:
        doc.custom_title = ""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def create_custom_fields_on_migrate():
    fields = {
        "Timesheet Detail" : [
            {
                "insert_after" : "completed",
                "fieldname" : "employee",
                "label" : "Employee",
                "fieldtype" : "Link",
                "options" : "Employee",
            }
        ],
        "Timesheet" : [
            {
                "insert_after" : "parent_project",
                "fieldname" : "job_card",
                "label" : "Job Card",
                "fieldtype" : "Link",
                "options" : "Job Card",
                "read_only" :  1
            }
        ],
        "Task" : [
            {
                "insert_after" : "depends_on",
                "fieldname" : "unproductive_work_timelogs",
                "label" : "Time Log",
                "fieldtype" : "Table",
                "options" : "Timesheet Detail",
                "hidden" :  1
            },
            {
                "insert_after" : "status",
                "fieldname" : "working_status",
                "label" : "Working Status",
                "fieldtype" : "Select",
                "options" : "\nWork In Progress\nOn Hold",
                "hidden" :  1
            },
            {
                "label": "Actual Progress",
                "fieldname": "custom_actual_progress",
                "insert_after": "act_end_date",
                "fieldtype": "Color",
                "default" : "#FFC067"
            },
            {
                "label": "Extra Days of Effort",
                "fieldname": "extra_days",
                "insert_after": "expected_time",
                "fieldtype": "Data",
                "read_only" : 1,
            }
        ],
        "Item Group" : [
            {
                "insert_after" : "is_group",
                "fieldname" : "user",
                "label" : "User",
                "fieldtype" : "Link",
                "options" : "User"
            }
        ],
        "Material Request" : [
            {
                "insert_after" : "custom_ba_number",
                "fieldname" : "item_group",
                "label" : "Item Group",
                "fieldtype" : "Link",
                "options" : "Item Group"
            },
            {
                "insert_after" : "items",
                "fieldname" : "total_items",
                "label" : "Total Number of Items",
                "fieldtype" : "Data",
                "read_only" : 1
            }
        ],
        "Production Plan" : [
            {
                "insert_after" : "transfer_materials",
                "fieldname" : "remove_based_item_group",
                "label" : "Commodity Group",
                "fieldtype" : "Table MultiSelect",
                "options" : "Removed As Per Item Group",
                "description" : "Update the Commodity Group to remove items from below table"
            },
            {
                "label": "Delete Selected Commodity Group Items",
                "fieldname": "delete_selected_commodity_group_items",
                "insert_after": "remove_based_item_group",
                "fieldtype": "Button",
            },
            {
                "label": "Deleted Selected Commodity Group Items",
                "fieldname": "deleted_selected_commodity_group_items",
                "insert_after": "delete_selected_commodity_group_items",
                "fieldtype": "Check",
                "hidden" : 1
            },
            {
                "insert_after" : "ignore_existing_ordered_qty",
                "fieldname" : "items_to_reduce_qty",
                "label" : "Items To Reduce Quantity",
                "fieldtype" : "Table MultiSelect",
                "options" : "Item To Reduce Quantity",
                "description" : "Update the Sub Assembly Item to reduce item from below table"
            },
            {
                "label" : "Reduce Item From Raw Material",
                "fieldname" : "reduce_item_from_raw_material",
                "insert_after" : "items_to_reduce_qty",
                "fieldtype" : "Button"
            },
            {
                "label" : "Removed Reduce Item From Raw Material",
                "fieldname" : "removed_reduce_item_from_raw_material",
                "insert_after" : "reduce_item_from_raw_material",
                "fieldtype" : "Check",
                "hidden" : 1
            },
            {
                "insert_after" : "skip_available_sub_assembly_item",
                "fieldname" : "remove_from_sub_and_raw",
                "label" : "Remove From Sub Assembly and Raw Material",
                "fieldtype" : "Table MultiSelect",
                "options" : "Item To Reduce Quantity"
            },
            {
                "label" : "Remove Sub-Assembly and Raw Materials",
                "fieldname" : "reduce_items",
                "insert_after" : "remove_from_sub_and_raw",
                "fieldtype" : "Button"
            },

        ],
        "Material Request Plan Item" : [
            {
                "label": "Commodity Group",
                "fieldname": "commodity_group",
                "insert_after": "item_code",
                "fieldtype": "Link",
                "options" : "Item Group",
                "read_only" : 0,
                "fetch_from" : "item_code.item_group"
            }
        ],
        "Projects Settings" : [
            {
                "fieldname" : "task_cut_of_time",
                "label" : "Task Cut of Time",
                "fieldtype" : "Float",
            },
            {
                "fieldname" : "job_card_cut_of_time",
                "label" : "Job Card Cut of Time",
                "fieldtype" : "Float",
            },
            {
                "fieldname" : "timesheet_cut_of_time",
                "label" : "Timesheet Cut Off Time",
                "fieldtype" : "Float",
                "insert_after" : "task_cut_of_time"
            }
        ],
        "Activity Type" : [
            {
                "fieldname" : "parent_activity_type",
                "label" : "Parent Activity",
                "fieldtype" : "Link",
                "options" : "Parent Activity",
                "insert_after" : "custom_unproductive_work"
            }
        ],
        "Travel Planning" : [
            {
                "fieldname" : "travel_requestor",
                "label" : "Travel Requestor",
                "fieldtype" : "Link",
                "options" : "Employee",
                "insert_after" : "travel_plan"
            }
        ],
        "Job Card Time Log" : [
            {
                "fieldname" : "activity_type",
                "label" : "Activity Type",
                "fieldtype" : "Link",
                "options" : "Activity Type",
                "insert_after" : "employee",
                "in_list_view" : 1
            }
        ],
        "Purchase Invoice" : [
            {
                "fieldname" : "travel_planning",
                "label" : "Travel Planning",
                "fieldtype" : "Link",
                "options" : "Travel Planning",
                "insert_after" : "due_date"
            },
            {
                "fieldname" : "from_goods_grn",
                "label" : "From Goods GRN",
                "fieldtype" : "Check",
                "insert_after" : "is_reverse_charge",
                "read_only" : 1
            }
        ],
        "Purchase Receipt Item" : [
            {
                "fieldname" : "ordered_qty_",
                "label" : "Ordered Qty",
                "fieldtype" : "Float",
                "insert_after" : "received_qty"
            },
            {
                "fieldname": "section_bil_invoice",
                "label": "",
                "fieldtype": "Section Break",
                "read_only": 0,
            },
            {
                "fieldname": "invoice_no",
                "label": "Invoice No",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after" : "section_bil_invoice"
            },
            {
                "fieldname": "column_bil_invoice",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after" : "invoice_no"
            },
            {
                "fieldname": "bill_of_entry",
                "label": "Bill of Entry",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after" : "column_bil_invoice"
            },
            {
                "fieldname": "section_bil_invoice_closed",
                "label": "",
                "fieldtype": "Section Break",
                "insert_after" : "bill_of_entry"
            },
        ],
        "Travel Itinerary" : [
            {
                "fieldname" : "room_night",
                "label" : "Room Night",
                "fieldtype" : "Int",
                "insert_after" : "check_out_date",
                "depends_on" : "eval:doc.lodging_required == 1;"
            }
        ],
        "Operation" : [
            {
                "fieldname" : "department",
                "label" : "Department",
                "fieldtype" : "Link",
                "insert_after" : "is_corrective_operation",
                "options" : "Department",
            }
        ],
        "Production Plan Sub Assembly Item" : [
            {
                "fieldname" : "structure_class",
                "label" : "Structure Class Head",
                "fieldtype" : "Data",
                "insert_after" : "supplier",
                "read_only" : 1,
                "fetch_from" : "production_item.custom_structure_class_head"
            }
        ],
        "Item" : [
            {
                "fieldname" : "is_allowed_without_po",
                "label" : "Is Allowed Without PO",
                "fieldtype" : "Check",
                "insert_after" : "is_grouped_asset"
            }
        ],
        "Travel Planning Employee Details": [
            {
                "fieldname": "reference_section",
                "label": "Reference Section",
                "fieldtype": "Section Break",
                "insert_after": "custom_taxi_required"
            },
            {
                "fieldname": "travel_request_itinerary",
                "label": "Travel Request Itinerary",
                "fieldtype": "Data",
                "insert_after": "reference",
                "hidden" : 1
            },
            {
                "fieldname": "flight_booking_email_sent",
                "label": "Flight Booking Email Sent",
                "fieldtype": "Check",
                "insert_after": "custom_flight_booking_details",
                "hidden": 1
            },
            {
                "fieldname": "hotel_booking_email_sent",
                "label": "Hotel Booking Email Sent",
                "fieldtype": "Check",
                "insert_after": "custom_hotel_booking_details",
                "hidden": 1
            }
        ],
        "Taxi" : [
            {
                "fieldname": "taxi_requestor",
                "label": "Taxi Requestor",
                "fieldtype": "Link",
                "options": "Employee",
                "insert_after": "is_paid"
            },
            {
                "fieldname": "taxi_requester_name",
                "label": "Taxi Requester Name",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "taxi_requestor",
                "fetch_from": "taxi_requestor.employee_name"
            },
            {
                "fieldname": "taxi_requester_email",
                "label": "Taxi Requestor Email",
                "fieldtype": "Data",
                "options": "Email",
                "read_only": 1,
                "insert_after": "taxi_requester_name",
                "fetch_from": "taxi_requestor.user_id"
            },
            {
                "fieldname": "taxi_requestor_team_lead",
                "label": "Taxi Requestor Team Lead",
                "fieldtype": "Link",
                "options": "User",
                "insert_after": "taxi_requester_name",
                "read_only": 1
            }
        ],
        "Batch" : [
            {
                "fieldname": "po_number",
                "label": "Po Number",
                "fieldtype": "Data",
                "insert_after": "invoice_no"
            },
            {
                "fieldname": "vender_name",
                "label": "Vender Name",
                "fieldtype": "Link",
                "options" : "Supplier",
                "insert_after": "po_number"
            },
            {
                "fieldname": "section_bil_invoice",
                "label": "",
                "fieldtype": "Section Break",
                "read_only": 0,
                "insert_after" : "sb_disabled"
            },
            {
                "fieldname": "invoice_no",
                "label": "Invoice No",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after" : "section_bil_invoice"
            },
            {
                "fieldname": "column_bil_invoice",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after" : "invoice_no"
            },
            {
                "fieldname": "bill_of_entry",
                "label": "Bill of Entry",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after" : "column_bil_invoice"
            },
            {
                "fieldname": "section_bil_invoice_closed",
                "label": "",
                "fieldtype": "Section Break",
                "read_only": 0,
                "insert_after" : "bill_of_entry"
            },
            {
                "fieldname": "rm_batch_details",
                "label": "RM Batch Details",
                "fieldtype": "Table",
                "options" : "RM Batch details",
                "read_only": 1,
                "insert_after" : "description"
            },
            {
                "fieldname": "rack",
                "label": "Target Rack",
                "fieldtype": "Link",
                "options": "Rack",
                "insert_after": "rm_batch_details"
            },
            {
                "fieldname": "rejected_rack",
                "label": "Rejected Rack",
                "fieldtype": "Link",
                "options": "Rack",
                "insert_after": "rack"
            },
            {
                "fieldname": "bin_location",
                "label": "Target Bin Location",
                "fieldtype": "Link",
                "options": "Bin Location",
                "insert_after": "rejected_rack"
            },
            {
                "fieldname": "rejected_bin_location",
                "label": "Rejected Bin Location",
                "fieldtype": "Link",
                "options": "Bin Location",
                "insert_after": "bin_location"
            }
        ],
        "Purchase Receipt": [
            {
                "fieldname": "import_details",
                "label": "Import Details",
                "fieldtype": "Tab Break",
                "insert_after": "other_details",
            },
            {
                "fieldname": "section_import_details",
                "label": "",
                "fieldtype": "Section Break",
                "insert_after": "import_details"
            },
            {
                "fieldname": "supplier_eway_bill_no",
                "label": "Supplier E-Way Bill No",
                "fieldtype": "Data",
                "insert_after": "section_import_details"
            },
            {
                "fieldname": "iec_no",
                "label": "IEC No",
                "fieldtype": "Data",
                "insert_after": "supplier_eway_bill_no"
            },
            {
                "fieldname": "port_code",
                "label": "Custom Station Of Import",
                "fieldtype": "Link",
                "options": "PORT CODE",
                "insert_after": "iec_no"
            },
            {
                "fieldname": "assessable_value_inr",
                "label": "Assessable Value (INR)",
                "fieldtype": "Currency",
                "insert_after": "port_code"
            },
            {
                "fieldname": "basic_custom_duty_inr",
                "label": "Basic Custom Duty (INR)",
                "fieldtype": "Currency",
                "insert_after": "assessable_value_inr"
            },
            {
                "fieldname": "tax_amount_inr",
                "label": "Tax Amount (INR)",
                "fieldtype": "Currency",
                "insert_after": "basic_custom_duty_inr"
            },
            {
                "fieldname": "insurance_no",
                "label": "Insurance No",
                "fieldtype": "Data",
                "options": "Insurance",
                "insert_after": "tax_amount_inr"
            },
            {
                "fieldname": "insurance_date",
                "label": "Insurance Date",
                "fieldtype": "Date",
                "insert_after": "insurance_no"
            },
            {
                "fieldname": "custom_column_break_qp2jh",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after": "insurance_date"
            },
            {
                "fieldname": "supplier_invoice_no",
                "label": "Supplier Invoice No",
                "fieldtype": "Data",
                "insert_after": "custom_mode_of_delivery",
            },
            {
                "fieldname": "supplier_invoice_date",
                "label": "Supplier Invoice Date",
                "fieldtype": "Date",
                "insert_after": "supplier_invoice_no",
            },
            {
                "fieldname": "bill_of_entry",
                "label": "Bill of Entry",
                "fieldtype": "Data",
                "insert_after": "custom_column_break_qp2jh",
            },
            {
                "fieldname": "bill_of_entry_date",
                "label": "Bill of Entry Date",
                "fieldtype": "Date",
                "insert_after": "bill_of_entry",
                "reqd": 0
            },
            {
                "fieldname": "bond_doc_type",
                "label": "Details of Bond",
                "fieldtype": "Data",
                "options": "Sea\nAir",
                "insert_after": "bill_of_entry_date"
            },
            {
                "fieldname": "bond_posting_date",
                "label": "Bond Posting Date",
                "fieldtype": "Date",
                "insert_after": "bond_doc_type"
            },
            {
                "fieldname": "bond_value_inr",
                "label": "Bond Value (INR)",
                "fieldtype": "Currency",
                "insert_after": "bond_posting_date"
            },
            {
                "fieldname": "bond_valid_till",
                "label": "Bond Valid Till",
                "fieldtype": "Date",
                "insert_after": "bond_value_inr"
            },
            {
                "fieldname": "transport_registration_no",
                "label": "Registration No. of means of transport",
                "fieldtype": "Data",
                "insert_after": "bond_valid_till"
            },
            {
                "fieldname": "vehicle_no",
                "label": "Vehicle No",
                "fieldtype": "Data",
                "insert_after": "insurance_date"
            },
            {
                "fieldname": "transporter_gst",
                "label": "Transporter GST",
                "fieldtype": "Data",
                "insert_after": "vehicle_no"
            },
            {
                "fieldname": "compensation_cess_inr",
                "label": "Compensation Cess (INR)",
                "fieldtype": "Currency",
                "insert_after": "tax_amount_inr"
            },
            {
                "fieldname": "lock_no",
                "label": "One-time Lock No",
                "fieldtype": "Data",
                "insert_after": "transport_registration_no"
            },
            {
                "fieldname": "goods_grn",
                "label": "Goods GRN",
                "fieldtype": "Check",
                "insert_after": "custom_customer_service",
                "read_only" : 1
            }
        ],
        "Expense Details" :[
            {
                "fieldname": "create_purchase_invoice",
                "label": "Create Purchase Invoice",
                "fieldtype": "Button",
                "insert_after": "profit"
            },
            {
               "fieldname": "invoice_attachment",
               "label": "Invoice Attachment",
               "fieldtype": "Attach",
               "insert_after": "service_type" 
            },
            {
                "fieldname": "send_email",
                "label": "Send Email",
                "fieldtype": "Button",
                "insert_after": "create_purchase_invoice"
            },
            {
                "fieldname": "email_sent",
                "label": "Email Sent",
                "fieldtype": "Check",
                "insert_after": "send_email",
                "default": 0,
                "read_only": 1,
                "hidden": 1
            }
        ],
        "Stock Entry Detail" : [
            {
                "fieldname": "po_number",
                "label": "Po Number",
                "fieldtype": "Data",
                "insert_after": "invoice_no"
            },
            {
                "fieldname": "vender_name",
                "label": "Vender Name",
                "fieldtype": "Link",
                "options" : "Supplier",
                "insert_after": "po_number"
            },
            {
                "fieldname": "section_bil_invoice",
                "label": "",
                "fieldtype": "Section Break",
                "read_only": 0,
            },
            {
                "fieldname": "invoice_no",
                "label": "Invoice No",
                "fieldtype": "Data",
                "read_only": 0,
                "insert_after" : "section_bil_invoice"
            },
            {
                "fieldname": "column_bil_invoice",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after" : "invoice_no"
            },
            {
                "fieldname": "bill_of_entry",
                "label": "Bill of Entry",
                "fieldtype": "Data",
                "read_only": 0,
                "insert_after" : "column_bil_invoice"
            },
            {
                "fieldname": "section_bil_invoice_closed",
                "label": "",
                "fieldtype": "Section Break",
                "read_only": 0,
                "insert_after" : "bill_of_entry"
            }
        ],
        "Stock Entry" : [
            {
                "fieldname": "import_details",
                "label": "Import Details",
                "fieldtype": "Tab Break",
                "insert_after": "total_additional_costs",
                "depends_on" : "eval:doc.stock_entry_type == 'Material Receipt'"
            },
            {
                "fieldname": "section_import_details",
                "label": "",
                "fieldtype": "Section Break",
                "insert_after": "import_details"
            },
            {
                "fieldname": "supplier_eway_bill_no",
                "label": "Supplier E-Way Bill No",
                "fieldtype": "Data",
                "insert_after": "section_import_details"
            },
            {
                "fieldname": "iec_no",
                "label": "IEC No",
                "fieldtype": "Data",
                "insert_after": "supplier_eway_bill_no"
            },
            {
                "fieldname": "port_code",
                "label": "Custom Station Of Import",
                "fieldtype": "Link",
                "options": "PORT CODE",
                "insert_after": "iec_no"
            },
            {
                "fieldname": "assessable_value_inr",
                "label": "Assessable Value (INR)",
                "fieldtype": "Currency",
                "insert_after": "port_code"
            },
            {
                "fieldname": "basic_custom_duty_inr",
                "label": "Basic Custom Duty (INR)",
                "fieldtype": "Currency",
                "insert_after": "assessable_value_inr"
            },
            {
                "fieldname": "tax_amount_inr",
                "label": "Tax Amount (INR)",
                "fieldtype": "Currency",
                "insert_after": "basic_custom_duty_inr"
            },
            {
                "fieldname": "insurance_no",
                "label": "Insurance No",
                "fieldtype": "Data",
                "options": "Insurance",
                "insert_after": "tax_amount_inr"
            },
            {
                "fieldname": "insurance_date",
                "label": "Insurance Date",
                "fieldtype": "Date",
                "insert_after": "insurance_no"
            },
            {
                "fieldname": "custom_column_break_qp2jh",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after": "insurance_date"
            },
            {
                "fieldname": "supplier_invoice_no",
                "label": "Supplier Invoice No",
                "fieldtype": "Data",
                "insert_after": "custom_column_break_qp2jh",
            },
            {
                "fieldname": "bill_of_entry",
                "label": "Bill of Entry",
                "fieldtype": "Data",
                "insert_after": "supplier_invoice_no",
            },
            {
                "fieldname": "bill_of_entry_date",
                "label": "Bill of Entry Date",
                "fieldtype": "Date",
                "insert_after": "bill_of_entry",
                "reqd": 1
            },
            {
                "fieldname": "bond_doc_type",
                "label": "Details of Bond",
                "fieldtype": "Data",
                "options": "Sea\nAir",
                "insert_after": "bill_of_entry_date"
            },
            {
                "fieldname": "bond_posting_date",
                "label": "Bond Posting Date",
                "fieldtype": "Date",
                "insert_after": "bond_doc_type"
            },
            {
                "fieldname": "bond_value_inr",
                "label": "Bond Value (INR)",
                "fieldtype": "Currency",
                "insert_after": "bond_posting_date"
            },
            {
                "fieldname": "bond_valid_till",
                "label": "Bond Valid Till",
                "fieldtype": "Date",
                "insert_after": "bond_value_inr"
            },
            {
                "fieldname": "transport_registration_no",
                "label": "Registration No. of means of transport",
                "fieldtype": "Data",
                "insert_after": "bond_valid_till"
            },
            {
                "fieldname": "vehicle_no",
                "label": "Vehicle No",
                "fieldtype": "Data",
                "insert_after": "insurance_date"
            },
            {
                "fieldname": "transporter_gst",
                "label": "Transporter GST",
                "fieldtype": "Data",
                "insert_after": "vehicle_no"
            },
            {
                "fieldname": "supplier_invoice_date",
                "label": "Supplier Invoice Date",
                "fieldtype": "Date",
                "insert_after": "supplier_invoice_no"
            },
            {
                "fieldname": "compensation_cess_inr",
                "label": "Compensation Cess (INR)",
                "fieldtype": "Currency",
                "insert_after": "tax_amount_inr"
            },
            {
                "fieldname": "lock_no",
                "label": "One-time Lock No",
                "fieldtype": "Data",
                "insert_after": "transport_registration_no"
            },
            {
                "fieldname": "delivery_challan_no",
                "label": "Delivery Challan No.",
                "fieldtype": "Data",
                "insert_after": "inspection_required",
                "depends_on": "eval:doc.stock_entry_type == 'Send to Subcontractor'",
                "mandatory_depends_on" : "eval:doc.stock_entry_type == 'Send to Subcontractor'",
                "reqd": 0
            },

        ],
        "Employee Visa Details" : [
            {
                "fieldname": "return_travel_date",
                "label": "Return Travel Date",
                "fieldtype": "Date",
                "insert_after": "entry"
            }
        ],
        "Purchase Order" : [
            {
                "fieldname": "expected_delivery_date",
                "label" : "Expected Delivery Date",
                "fieldtype" : "Date",
                "insert_after" : "custom_email_communication"
            }
        ],
        "Accounts Settings" : [
            {
                "fieldname": "due_date_calculation_section",
                "label": "Due Date Calculation",
                "fieldtype": "Section Break",
                "insert_after": "show_party_balance"
            },
            {
                "fieldname": "due_date_calculation_not_based_on_supplier_invoice_no",
                "label": "Due date calculation not based on supplier invoice no",
                "fieldtype": "Check",
                "insert_after": "due_date_calculation_section",
                "default": "0"
            }
        ],
        "Bank Statement Import" : [
            {
                "fieldname": "currency",
                "label": "Currency",
                "fieldtype": "Link",
                "options": "Currency",
                "reqd": 1,
                "insert_after": "bank"
            },
            {
                "fieldname": "unprocessed_file",
                "label": "Unprocessed File",
                "fieldtype": "Attach",
                "insert_after": "html_5"
            },
            {
                "fieldname": "process",
                "label": "Process",
                "fieldtype": "Button",
                "insert_after": "unprocessed_file"
            }
        ]
        
    }

    create_custom_fields(fields)

    from harro.patches.migrate_data_to_standard_field import update_purchase_receipt_invoice_fields

    update_purchase_receipt_invoice_fields()

    if frappe.get_meta("Purchase Receipt").has_field("custom_supplier_invoice_no"):
        frappe.db.delete("Custom Field", "Purchase Receipt-custom_supplier_invoice_no")
    
    if frappe.get_meta("Purchase Receipt").has_field("custom_supplier_invoice_date"):
        frappe.db.delete("Custom Field", "Purchase Receipt-custom_supplier_invoice_date")
    

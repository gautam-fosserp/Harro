import frappe
from frappe.utils.background_jobs import enqueue


def start_stock_entry_cancellation():
    """Start the cancellation process."""

    stock_entries = frappe.get_all(
        "Stock Entry",
        filters={"docstatus": 1},
        order_by="posting_date asc, posting_time asc, creation asc",
        pluck="name",
    )

    if not stock_entries:
        frappe.logger().info("No submitted Stock Entries found.")
        return

    enqueue(
        cancel_stock_entry,
        queue="long",
        stock_entries=stock_entries,
        index=0,
    )


def cancel_stock_entry(stock_entries, index):
    """Cancel one Stock Entry and enqueue the next."""

    if index >= len(stock_entries):
        frappe.logger().info("All Stock Entries cancelled successfully.")
        return

    name = stock_entries[index]

    try:
        frappe.db.commit()

        doc = frappe.get_doc("Stock Entry", name)

        if doc.docstatus == 1:
            doc.cancel()
            frappe.db.commit()
            frappe.logger().info(f"Cancelled {name}")

    except Exception:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(),
            f"Failed to cancel Stock Entry {name}"
        )

    # Queue the next Stock Entry only after this one finishes
    enqueue(
        cancel_stock_entry,
        queue="long",
        stock_entries=stock_entries,
        index=index + 1,
    )


# Start the process
start_stock_entry_cancellation()
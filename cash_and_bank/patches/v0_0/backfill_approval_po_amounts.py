# Copyright (c) 2026, ATS Synthetic (Pvt) Ltd. and contributors
# For license information, please see license.txt

import frappe

from cash_and_bank.cash_and_bank.doctype.approval_for_payment.approval_for_payment import (
	get_purchase_order_details,
)


def execute():
	"""Re-sync Dated/Amount on every existing Approval for Payment PO row
	(draft, submitted and cancelled) from its Purchase Order. Rows saved
	before this logic existed have Amount 0 or a hand-typed figure."""
	frappe.reload_doc("cash_and_bank", "doctype", "approval_for_payment_purchase_order")

	rows = frappe.get_all(
		"Approval for Payment Purchase Order",
		filters={"parenttype": "Approval for Payment"},
		fields=["name", "purchase_order"],
	)
	for row in rows:
		details = get_purchase_order_details(row.purchase_order)
		frappe.db.set_value(
			"Approval for Payment Purchase Order",
			row.name,
			{"dated": details["dated"], "amount": details["amount"]},
			update_modified=False,
		)

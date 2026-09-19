# Copyright (c) 2026, ATS Synthetic (Pvt) Ltd. and contributors
# For license information, please see license.txt

import frappe


def set_mode_of_payment_type(doc, method=None):
	"""Keeps `custom_mode_of_payment_type` on Payment Entry in sync with the
	`type` (Cash / Bank / General) of the linked Mode of Payment.

	Frappe's list view can't filter directly on a field that lives on a
	*linked* doctype (Mode of Payment.type), so we mirror it onto Payment
	Entry itself. This is what actually powers "Cash Payments" / "Bank
	Payments" / "Cash Receipts" / "Bank Receipts" in the Cash & Bank sidebar —
	every Payment Entry whose Mode of Payment is typed Cash or Bank lands in
	the matching filtered list.
	"""
	if not doc.mode_of_payment:
		doc.custom_mode_of_payment_type = ""
		return

	mop_type = frappe.db.get_value("Mode of Payment", doc.mode_of_payment, "type")
	doc.custom_mode_of_payment_type = mop_type or ""


def backfill_existing_payment_entries():
	"""One-time backfill run from the install patch so historical Payment
	Entries also become filterable immediately, without waiting for the
	next save."""
	rows = frappe.db.sql(
		"""
		select pe.name, mop.type
		from `tabPayment Entry` pe
		inner join `tabMode of Payment` mop on mop.name = pe.mode_of_payment
		where ifnull(pe.custom_mode_of_payment_type, '') = ''
		""",
		as_dict=True,
	)
	for row in rows:
		frappe.db.set_value(
			"Payment Entry", row.name, "custom_mode_of_payment_type", row.type or "", update_modified=False
		)


@frappe.whitelist()
def get_amount_in_words(amount, company=None):
	"""Powers the live 'Zero Only' style preview under the Amount field in
	the Write Cheque wizard."""
	from frappe.utils import flt, money_in_words

	company_currency = frappe.db.get_value("Company", company, "default_currency") if company else None
	return money_in_words(flt(amount), company_currency)

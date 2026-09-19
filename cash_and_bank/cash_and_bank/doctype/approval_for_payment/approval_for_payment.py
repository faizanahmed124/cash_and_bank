# Copyright (c) 2026, ATS Synthetic (Pvt) Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, money_in_words


class ApprovalforPayment(Document):
	def validate(self):
		self.set_payable_account()
		self.calculate_totals()
		self.set_in_words()

	def set_payable_account(self):
		"""Mirror onSupplierChange() in the prototype: fetch the supplier's
		payable account for the selected company."""
		if self.supplier and self.company:
			try:
				from erpnext.accounts.party import get_party_account

				self.payable_account = get_party_account(
					"Supplier", self.supplier, self.company
				)
			except Exception:
				# fall back silently if erpnext party utils are unavailable
				pass

		if self.purchase_invoice:
			self.invoice_date = frappe.db.get_value(
				"Purchase Invoice", self.purchase_invoice, "posting_date"
			)

	def calculate_totals(self):
		"""Exact server-side mirror of the calc() function in the
		Cash & Bank prototype's client script.

		Every field pulled off `self` here is explicitly run through flt()
		before being used in arithmetic: on a brand-new unsaved doc, Percent/
		Currency fields can still be plain strings (e.g. "18.000") when
		validate() first runs, and `float * str` raises
		"can't multiply sequence by non-int of type 'float'".
		"""
		value_ex_tax = flt(self.value_ex_tax)
		sales_tax_rate = flt(self.sales_tax_rate)
		itax_rate = flt(self.itax_rate)
		stw_rate = flt(self.stw_rate)

		if sales_tax_rate:
			self.sales_tax = flt(value_ex_tax * sales_tax_rate / 100, 2)
		else:
			self.sales_tax = flt(self.sales_tax)

		self.total_value = flt(value_ex_tax + self.sales_tax, 2)

		taxable_base = self.total_value  # confirm exact base with Accounts team

		if itax_rate:
			self.itax_amount = flt(taxable_base * itax_rate / 100, 2)
		else:
			self.itax_amount = flt(self.itax_amount)

		if stw_rate:
			self.stw_amount = flt(taxable_base * stw_rate / 100, 2)
		else:
			self.stw_amount = flt(self.stw_amount)

		self.net_payment = flt(
			self.total_value
			- flt(self.less_advance)
			- flt(self.itax_amount)
			- flt(self.stw_amount)
			- flt(self.other_deduction),
			2,
		)

	def set_in_words(self):
		company_currency = frappe.db.get_value("Company", self.company, "default_currency") if self.company else None
		self.in_words = money_in_words(self.net_payment, company_currency)


def on_submit(doc, method=None):
	frappe.msgprint(
		_("Approval for Payment {0} submitted for Rs. {1} in favour of {2}.").format(
			frappe.bold(doc.name), frappe.bold(doc.get_formatted("net_payment")), frappe.bold(doc.supplier)
		),
		alert=True,
		indicator="green",
	)


@frappe.whitelist()
def make_payment_entry(source_name, target_doc=None):
	"""Bridge from the custom Approval for Payment doc to ERPNext's
	standard Payment Entry — keeps actual money movement inside the
	core ERPNext doctype rather than duplicating it here."""
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_type = "Pay"
		target.party_type = "Supplier"
		target.party = source.supplier
		target.paid_amount = source.net_payment
		target.received_amount = source.net_payment
		target.mode_of_payment = source.mode_of_payment
		target.reference_no = source.name
		target.reference_date = source.posting_date
		if source.purchase_invoice:
			target.append(
				"references",
				{
					"reference_doctype": "Purchase Invoice",
					"reference_name": source.purchase_invoice,
					"allocated_amount": source.net_payment,
				},
			)

	doc = get_mapped_doc(
		"Approval for Payment",
		source_name,
		{
			"Approval for Payment": {
				"doctype": "Payment Entry",
				"field_map": {"company": "company"},
			}
		},
		target_doc,
		set_missing_values,
	)
	return doc


@frappe.whitelist()
def create_cheque(source_name, values):
	"""Called from the "Write Cheque" wizard on a submitted Approval for
	Payment. Creates a real Cheque record (feeding the Cheque Register)
	pre-filled from whatever the user confirmed in the wizard, and returns
	its name so the client can open it straight in the print view — that
	print view's own Print/PDF button is the "Cheque Print" action."""
	if isinstance(values, str):
		values = json.loads(values)

	source = frappe.get_doc("Approval for Payment", source_name)

	if source.docstatus != 1:
		frappe.throw(_("Cheque can only be created against a submitted Approval for Payment."))

	cheque = frappe.new_doc("Cheque")
	cheque.approval_for_payment = source.name
	cheque.company = source.company
	cheque.cheque_date = values.get("cheque_date")
	cheque.pay_to_order_of = values.get("pay_to_order_of")
	cheque.amount = flt(values.get("amount"))
	cheque.bank_account_no = values.get("bank_account_no")
	cheque.title = values.get("title")
	cheque.ac_payees_only = values.get("ac_payees_only")
	cheque.amount_not_greater_than = flt(values.get("amount_not_greater_than"))
	cheque.status = "Printed"
	cheque.insert(ignore_permissions=True)

	return cheque.name

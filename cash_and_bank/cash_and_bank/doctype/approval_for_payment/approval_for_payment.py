# Copyright (c) 2026, ATS Synthetic (Pvt) Ltd. and contributors
# For license information, please see license.txt

import json
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, money_in_words


def round_half_up(value):
	"""Round to the nearest whole rupee, with .5 always going away from zero
	(5.5 -> 6, 5.4 -> 5, -5.5 -> -6). Python's round() and flt(x, 0) can use
	banker's rounding (2.5 -> 2), so go through Decimal instead. The value is
	first trimmed to 6 decimals so float noise like 2.4999999999 doesn't
	round the wrong way."""
	d = Decimal(str(round(flt(value), 6)))
	return flt(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class ApprovalforPayment(Document):
	def validate(self):
		self.set_payable_account()
		self.set_purchase_order_details()
		self.set_bank_details()
		self.calculate_totals()
		self.set_in_words()

	def set_purchase_order_details(self):
		"""Always re-read Dated/Amount from the linked Purchase Order so the
		rows can't drift from the PO (e.g. after the PO is amended)."""
		for row in self.get("purchase_orders"):
			details = get_purchase_order_details(row.purchase_order)
			row.dated = details.get("dated")
			row.amount = details.get("amount")

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

	def set_bank_details(self):
		"""Bank counterpart of set_payable_account(): pull the account no.
		and GL account off the selected Bank Account, and make sure it is
		one of this company's accounts at the chosen bank."""
		if self.payment_mode != "Bank":
			self.bank = self.bank_account = self.bank_account_no = self.paid_from_account = None
			return

		if not self.bank_account:
			self.bank_account_no = self.paid_from_account = None
			return

		ba = frappe.db.get_value(
			"Bank Account",
			self.bank_account,
			["bank", "company", "is_company_account", "bank_account_no", "account"],
			as_dict=True,
		)
		if not ba:
			return

		if self.bank and ba.bank != self.bank:
			frappe.throw(_("Bank Account {0} does not belong to bank {1}.").format(
				frappe.bold(self.bank_account), frappe.bold(self.bank)
			))
		if not ba.is_company_account or (self.company and ba.company != self.company):
			frappe.throw(_("Bank Account {0} is not a company account of {1}.").format(
				frappe.bold(self.bank_account), frappe.bold(self.company)
			))

		self.bank = ba.bank
		self.bank_account_no = ba.bank_account_no
		self.paid_from_account = ba.account

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
			self.sales_tax = round_half_up(value_ex_tax * sales_tax_rate / 100)
		else:
			self.sales_tax = round_half_up(self.sales_tax)

		self.total_value = round_half_up(value_ex_tax + self.sales_tax)

		taxable_base = self.total_value  # confirm exact base with Accounts team

		if itax_rate:
			self.itax_amount = round_half_up(taxable_base * itax_rate / 100)
		else:
			self.itax_amount = round_half_up(self.itax_amount)

		if stw_rate:
			self.stw_amount = round_half_up(taxable_base * stw_rate / 100)
		else:
			self.stw_amount = round_half_up(self.stw_amount)

		self.net_payment = round_half_up(
			self.total_value
			- flt(self.less_advance)
			- flt(self.itax_amount)
			- flt(self.stw_amount)
			- flt(self.other_deduction)
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


def get_purchase_order_details(purchase_order):
	"""Dated + Amount for a PO row. Amount is the PO's Rounded Total, i.e. what
	is actually payable; falls back to Grand Total when rounding is disabled
	on the PO (rounded_total is 0 then)."""
	if not purchase_order:
		return {"dated": None, "amount": 0}

	po = frappe.db.get_value(
		"Purchase Order",
		purchase_order,
		["transaction_date", "grand_total", "rounded_total"],
		as_dict=True,
	)
	if not po:
		return {"dated": None, "amount": 0}

	return {
		"dated": po.transaction_date,
		"amount": flt(po.rounded_total) or flt(po.grand_total),
	}


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
		if source.bank_account:
			target.bank_account = source.bank_account
		if source.paid_from_account:
			target.paid_from = source.paid_from_account
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

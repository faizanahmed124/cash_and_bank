# Copyright (c) 2026, ATS Synthetic (Pvt) Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import money_in_words


class Cheque(Document):
	def validate(self):
		company_currency = (
			frappe.db.get_value("Company", self.company, "default_currency") if self.company else None
		)
		self.amount_in_words = money_in_words(self.amount, company_currency)

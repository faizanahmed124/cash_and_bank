app_name = "cash_and_bank"
app_title = "Cash and Bank"
app_publisher = "ATS Synthetic (Pvt) Ltd."
app_description = "Cash & Bank workspace on top of ERPNext — Approval for Payment, Cheque wizard, plus curated views onto standard Payment Entry, Banking and Reconciliation tools."
app_email = "it@atssynthetic.com"
app_license = "MIT"
app_icon = "octicon octicon-briefcase"
app_color = "#2490ef"

required_apps = ["frappe", "erpnext"]

app_include_js = "/assets/cash_and_bank/js/cash_and_bank.js"

fixtures = [
	{
		"doctype": "Mode of Payment",
		"filters": [["name", "in", ["Cash", "Meezan Bank", "HBL", "Bank Transfer", "Cheque"]]],
	}
]

doc_events = {
	"Approval for Payment": {
		"on_submit": "cash_and_bank.cash_and_bank.doctype.approval_for_payment.approval_for_payment.on_submit",
	},
	"Payment Entry": {
		"validate": "cash_and_bank.cash_and_bank.utils.set_mode_of_payment_type",
	},
}

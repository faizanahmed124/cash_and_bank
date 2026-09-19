// Copyright (c) 2026, ATS Synthetic (Pvt) Ltd. and contributors
// For license information, please see license.txt

const DEFAULT_DOCS_ATTACHED = [
	["P.O", "Purchase Order"],
	["D.C", "Delivery Note"],
	["I.G.P", "Custom IGP"],
	["G.R.N", "Purchase Receipt"],
	["S. Tax Invoice", "Purchase Invoice"],
	["Bill", "Purchase Invoice"],
	["Check by Q.C", "Quality Inspection"],
	["I. Tax Exemption Certificate", "Attachment only"],
	["S. Tax w. Tax Exemption Certificate", "Attachment only"],
	["Active Taxpayer", "Attachment only"],
];

frappe.ui.form.on("Approval for Payment", {
	setup(frm) {
		frm.set_query("purchase_invoice", () => ({
			filters: {
				supplier: frm.doc.supplier,
				docstatus: 1,
			},
		}));

		frm.set_query("mode_of_payment", () => ({
			filters: frm.doc.payment_mode ? { type: frm.doc.payment_mode } : {},
		}));
	},

	onload(frm) {
		if (frm.is_new()) {
			if (!frm.doc.company) {
				frm.set_value("company", frappe.defaults.get_default("company"));
			}
			if (!(frm.doc.documents_attached || []).length) {
				DEFAULT_DOCS_ATTACHED.forEach(([label, ref]) => {
					frm.add_child("documents_attached", {
						document_label: label,
						linked_doctype: ref,
						attached: 0,
					});
				});
				frm.refresh_field("documents_attached");
			}
			if (!(frm.doc.purchase_orders || []).length) {
				frm.set_value("payment_mode", "Bank");
			}
		}
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Payment Entry"),
				() => {
					frappe.model.open_mapped_doc({
						method:
							"cash_and_bank.cash_and_bank.doctype.approval_for_payment.approval_for_payment.make_payment_entry",
						frm: frm,
					});
				},
				__("Create")
			);

			if (frm.doc.payment_mode === "Bank") {
				frm.add_custom_button(
					__("Cheque"),
					() => open_write_cheque_dialog(frm),
					__("Create")
				);
			}
		}
	},

	supplier(frm) {
		frm.set_value("purchase_invoice", "");
		frm.set_value("invoice_date", "");
		frm.set_value("payable_account", "");

		if (!frm.doc.supplier || !frm.doc.company) return;

		frappe.call({
			method: "erpnext.accounts.party.get_party_account",
			args: {
				party_type: "Supplier",
				party: frm.doc.supplier,
				company: frm.doc.company,
			},
			callback(r) {
				if (r.message) {
					frm.set_value("payable_account", r.message);
				}
			},
		});
	},

	purchase_invoice(frm) {
		if (frm.doc.purchase_invoice) {
			frappe.db.get_value("Purchase Invoice", frm.doc.purchase_invoice, "posting_date").then((r) => {
				frm.set_value("invoice_date", r.message.posting_date);
			});
		} else {
			frm.set_value("invoice_date", "");
		}
	},

	payment_mode(frm) {
		if (frm.doc.payment_mode) {
			frappe.db
				.get_list("Mode of Payment", {
					filters: { type: frm.doc.payment_mode },
					limit: 1,
				})
				.then((rows) => {
					if (rows && rows.length && !frm.doc.mode_of_payment) {
						frm.set_value("mode_of_payment", rows[0].name);
					}
				});
		}
	},

	mode_of_payment(frm) {
		if (!frm.doc.mode_of_payment) return;
		frappe.db.get_value("Mode of Payment", frm.doc.mode_of_payment, "type").then((r) => {
			const type = r.message.type === "Cash" ? "Cash" : "Bank";
			if (type !== frm.doc.payment_mode) {
				frm.set_value("payment_mode", type);
			}
		});
	},

	value_ex_tax: calc,
	sales_tax_rate: calc,
	sales_tax: calc,
	less_advance: calc,
	itax_rate: calc,
	itax_amount: calc,
	stw_rate: calc,
	stw_amount: calc,
	other_deduction: calc,
});

function calc(frm) {
	// Client-side preview only — the server recomputes everything in
	// validate() with the same formulas, and that's the source of truth.
	const value_ex_tax = flt(frm.doc.value_ex_tax);
	let sales_tax = flt(frm.doc.sales_tax);
	if (flt(frm.doc.sales_tax_rate)) {
		sales_tax = flt((value_ex_tax * frm.doc.sales_tax_rate) / 100, 2);
		frm.set_value("sales_tax", sales_tax);
	}

	const total_value = flt(value_ex_tax + sales_tax, 2);
	frm.set_value("total_value", total_value);

	let itax_amount = flt(frm.doc.itax_amount);
	if (flt(frm.doc.itax_rate)) {
		itax_amount = flt((total_value * frm.doc.itax_rate) / 100, 2);
		frm.set_value("itax_amount", itax_amount);
	}

	let stw_amount = flt(frm.doc.stw_amount);
	if (flt(frm.doc.stw_rate)) {
		stw_amount = flt((total_value * frm.doc.stw_rate) / 100, 2);
		frm.set_value("stw_amount", stw_amount);
	}

	const net_payment = flt(
		total_value - flt(frm.doc.less_advance) - itax_amount - stw_amount - flt(frm.doc.other_deduction),
		2
	);
	frm.set_value("net_payment", net_payment);
}

function flt(v) {
	return frappe.utils && frappe.utils.flt ? frappe.utils.flt(v) : parseFloat(v) || 0;
}

// ---------------------------------------------------------------------
// "Write Cheque" wizard — modelled on the legacy Cheque Register screen.
// Creates a real Cheque record, then opens it straight in the print view
// where the dialog's "Cheque Print" action hands off to Frappe's own
// Print/PDF controls.
// ---------------------------------------------------------------------
function open_write_cheque_dialog(frm) {
	const supplier_name_promise = frm.doc.supplier
		? frappe.db.get_value("Supplier", frm.doc.supplier, "supplier_name").then((r) => r.message.supplier_name)
		: Promise.resolve("");

	supplier_name_promise.then((supplier_name) => {
		const dialog = new frappe.ui.Dialog({
			title: __("Write Cheque"),
			fields: [
				{
					fieldname: "pay_to_order_of",
					fieldtype: "Data",
					label: __("Pay To The Order Of"),
					default: supplier_name || frm.doc.supplier,
					reqd: 1,
				},
				{ fieldname: "cb_col_1", fieldtype: "Column Break" },
				{
					fieldname: "cheque_date",
					fieldtype: "Date",
					label: __("Date"),
					default: frappe.datetime.get_today(),
					reqd: 1,
				},
				{ fieldname: "cb_sec_amount", fieldtype: "Section Break" },
				{
					fieldname: "amount",
					fieldtype: "Currency",
					label: __("Amount (Rs.)"),
					default: frm.doc.net_payment,
					reqd: 1,
					options: "Company:company:default_currency",
					onchange() {
						update_words_preview(dialog, frm);
					},
				},
				{
					fieldname: "amount_in_words",
					fieldtype: "Data",
					label: __("In Words"),
					read_only: 1,
				},
				{ fieldname: "cb_col_2", fieldtype: "Column Break" },
				{
					fieldname: "bank_account_no",
					fieldtype: "Data",
					label: __("Bank A/c No:"),
				},
				{
					fieldname: "title",
					fieldtype: "Data",
					label: __("Title:"),
				},
				{ fieldname: "cb_sec_checks", fieldtype: "Section Break" },
				{
					fieldname: "ac_payees_only",
					fieldtype: "Check",
					label: __("A/c Payees Only"),
					default: 1,
				},
				{ fieldname: "cb_col_3", fieldtype: "Column Break" },
				{
					fieldname: "amount_not_greater_than",
					fieldtype: "Currency",
					label: __("Amount Not Greater Then"),
					options: "Company:company:default_currency",
				},
			],
			primary_action_label: __("Cheque Print"),
			primary_action(values) {
				frappe.call({
					method:
						"cash_and_bank.cash_and_bank.doctype.approval_for_payment.approval_for_payment.create_cheque",
					args: {
						source_name: frm.doc.name,
						values: values,
					},
					freeze: true,
					freeze_message: __("Creating Cheque..."),
					callback(r) {
						if (r.message) {
							dialog.hide();
							frappe.show_alert({
								message: __("Cheque {0} created", [r.message]),
								indicator: "green",
							});
							frappe.set_route("print", "Cheque", r.message);
						}
					},
				});
			},
			secondary_action_label: __("Close"),
			secondary_action() {
				dialog.hide();
			},
		});

		dialog.show();
		update_words_preview(dialog, frm);
	});
}

function update_words_preview(dialog, frm) {
	const amount = dialog.get_value("amount");
	frappe.call({
		method: "cash_and_bank.cash_and_bank.utils.get_amount_in_words",
		args: { amount: amount, company: frm.doc.company },
		callback(r) {
			if (r.message !== undefined) {
				dialog.set_value("amount_in_words", r.message);
			}
		},
	});
}

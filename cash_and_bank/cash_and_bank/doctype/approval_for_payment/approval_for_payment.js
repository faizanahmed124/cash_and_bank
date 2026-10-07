// Copyright (c) 2026, ATS Synthetic (Pvt) Ltd. and contributors
// For license information, please see license.txt

// `var`, not `const`: Frappe can eval this script more than once per page
// (e.g. after a doctype reload in developer mode), and redeclaring a
// top-level const throws, killing every handler in this file.
var DEFAULT_DOCS_ATTACHED = [
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

		// Draft + submitted POs; cancelled ones are never payable.
		frm.set_query("purchase_order", "purchase_orders", () => ({
			filters: {
				supplier: frm.doc.supplier,
				docstatus: ["!=", 2],
			},
		}));

		frm.set_query("mode_of_payment", () => ({
			filters: frm.doc.payment_mode ? { type: frm.doc.payment_mode } : {},
		}));

		frm.set_query("bank_account", () => ({
			filters: company_bank_account_filters(frm),
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

	company(frm) {
		frm.set_value("bank_account", "");
		frm.trigger("bank");
	},

	bank(frm) {
		// Same idea as supplier -> payable_account: picking the bank fills
		// in the company's account at that bank (default one first).
		// Bank A/c No. and the GL account then come in via fetch_from.
		frm.set_value("bank_account", "");
		if (!frm.doc.bank || !frm.doc.company) return;

		frappe.db
			.get_list("Bank Account", {
				filters: company_bank_account_filters(frm),
				order_by: "is_default desc, modified desc",
				limit: 1,
			})
			.then((rows) => {
				if (rows && rows.length) {
					frm.set_value("bank_account", rows[0].name);
				} else {
					frappe.show_alert({
						message: __("No Bank Account found for {0} in {1}", [frm.doc.bank, frm.doc.company]),
						indicator: "orange",
					});
				}
			});
	},

	payment_mode(frm) {
		if (frm.doc.payment_mode !== "Bank") {
			frm.set_value("bank", "");
			frm.set_value("bank_account", "");
		}
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

frappe.ui.form.on("Approval for Payment Purchase Order", {
	purchase_order(frm, cdt, cdn) {
		// Preview only — validate() re-reads these from the PO on every save.
		// Same rule as get_purchase_order_details() in the .py.
		const row = locals[cdt][cdn];
		if (!row.purchase_order) {
			frappe.model.set_value(cdt, cdn, { dated: "", amount: 0 });
			return;
		}
		frappe.db
			.get_value("Purchase Order", row.purchase_order, ["transaction_date", "grand_total", "rounded_total"])
			.then((r) => {
				const po = r.message || {};
				frappe.model.set_value(cdt, cdn, {
					dated: po.transaction_date,
					amount: flt(po.rounded_total) || flt(po.grand_total),
				});
			});
	},
});

function calc(frm) {
	// Client-side preview only — the server recomputes everything in
	// validate() with the same formulas, and that's the source of truth.
	const value_ex_tax = flt(frm.doc.value_ex_tax);
	let sales_tax = round_half_up(frm.doc.sales_tax);
	if (flt(frm.doc.sales_tax_rate)) {
		sales_tax = round_half_up((value_ex_tax * frm.doc.sales_tax_rate) / 100);
	}
	frm.set_value("sales_tax", sales_tax);

	const total_value = round_half_up(value_ex_tax + sales_tax);
	frm.set_value("total_value", total_value);

	let itax_amount = round_half_up(frm.doc.itax_amount);
	if (flt(frm.doc.itax_rate)) {
		itax_amount = round_half_up((total_value * frm.doc.itax_rate) / 100);
	}
	frm.set_value("itax_amount", itax_amount);

	let stw_amount = round_half_up(frm.doc.stw_amount);
	if (flt(frm.doc.stw_rate)) {
		stw_amount = round_half_up((total_value * frm.doc.stw_rate) / 100);
	}
	frm.set_value("stw_amount", stw_amount);

	const net_payment = round_half_up(
		total_value - flt(frm.doc.less_advance) - itax_amount - stw_amount - flt(frm.doc.other_deduction)
	);
	frm.set_value("net_payment", net_payment);
}

function company_bank_account_filters(frm) {
	const filters = { is_company_account: 1, disabled: 0 };
	if (frm.doc.company) filters.company = frm.doc.company;
	if (frm.doc.bank) filters.bank = frm.doc.bank;
	return filters;
}

// NOTE: don't define helpers named flt/cint/etc. here — Frappe evals form
// scripts in the global scope, so they'd replace Frappe's own globals for
// the whole desk. Frappe's global flt() is used below.

// Same as round_half_up() in approval_for_payment.py: nearest whole rupee,
// .5 goes away from zero (5.5 -> 6, -5.5 -> -6). Trimming to 6 decimals
// first stops float noise like 2.4999999999 rounding the wrong way.
function round_half_up(v) {
	const n = Number(flt(v).toFixed(6));
	return Math.sign(n) * Math.round(Math.abs(n));
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
					default: frm.doc.bank_account_no,
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

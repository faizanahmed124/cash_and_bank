# Copyright (c) 2026, ATS Synthetic (Pvt) Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

from cash_and_bank.cash_and_bank.utils import backfill_existing_payment_entries
from cash_and_bank.cash_and_bank.sidebar_html import (
	SIDEBAR_BLOCK_NAME,
	get_sidebar_html,
	get_sidebar_script,
	get_sidebar_style,
)


def execute():
	# 1) The real Cash/Bank filter field -- this part must succeed, it's the
	# actual mechanism behind "Cash Payments" / "Bank Payments" etc.
	frappe.reload_doc("core", "doctype", "custom_field")

	create_custom_field(
		"Payment Entry",
		{
			"fieldname": "custom_mode_of_payment_type",
			"label": "Mode of Payment Type",
			"fieldtype": "Select",
			"options": "\nCash\nBank\nGeneral",
			"insert_after": "mode_of_payment",
			"read_only": 1,
			"hidden": 1,
			"in_standard_filter": 1,
			"in_list_view": 0,
			"no_copy": 1,
		},
	)

	backfill_existing_payment_entries()

	# 2) The pixel-styled sidebar is cosmetic -- never let it break the
	# migration. If your Frappe version's Custom HTML Block schema differs,
	# this step just skips itself and prints where to add it manually.
	try:
		install_sidebar_block()
	except Exception:
		frappe.log_error(title="Cash and Bank: sidebar block install skipped")
		frappe.msgprint(
			"Could not auto-install the Cash & Bank sidebar block (this is "
			"purely cosmetic -- everything else in the app is unaffected). "
			"See the README for how to add it by hand from the Workspace "
			"editor.",
			indicator="orange",
			alert=True,
		)


def install_sidebar_block():
	if not frappe.db.exists("DocType", "Custom HTML Block"):
		frappe.msgprint(
			"This Frappe version has no 'Custom HTML Block' doctype, so the "
			"pixel-styled Cash & Bank sidebar could not be installed. "
			"The app's regular workspace cards are used instead.",
			indicator="orange",
			alert=True,
		)
		return

	values = {
		"html": get_sidebar_html(),
		"style": get_sidebar_style(),
		"script": get_sidebar_script(),
	}

	if frappe.db.exists("Custom HTML Block", SIDEBAR_BLOCK_NAME):
		block = frappe.get_doc("Custom HTML Block", SIDEBAR_BLOCK_NAME)
		block.update(values)
		block.save(ignore_permissions=True)
	else:
		block = frappe.new_doc("Custom HTML Block")
		block.name = SIDEBAR_BLOCK_NAME
		block.update(values)
		if hasattr(block, "private"):
			block.private = 0
		block.insert(ignore_permissions=True)

	frappe.db.commit()
	add_block_to_workspace()


def add_block_to_workspace():
	"""Best-effort: try to slot the sidebar block into the Cash and Bank
	workspace's content automatically. If your Frappe version stores the
	custom-block reference under a different JSON key, this silently
	no-ops -- open the workspace in edit mode and add the block by hand
	instead (Edit > Add Block > Custom Block > 'Cash and Bank Sidebar')."""
	import json

	if not frappe.db.exists("Workspace", "Cash and Bank"):
		return

	ws = frappe.get_doc("Workspace", "Cash and Bank")
	try:
		blocks = json.loads(ws.content or "[]")
	except Exception:
		return

	already_present = any(b.get("type") == "custom_block" for b in blocks)
	if already_present:
		return

	blocks.append(
		{
			"id": "cb_sidebar_block",
			"type": "custom_block",
			"data": {"block_name": SIDEBAR_BLOCK_NAME, "col": 4},
		}
	)
	ws.content = json.dumps(blocks)
	ws.save(ignore_permissions=True)
	frappe.db.commit()

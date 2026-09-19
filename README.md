# Cash and Bank

A custom Frappe app for **ERPNext**: an **Approval for Payment** DocType,
a **Write Cheque** wizard that generates real Cheque records, and a
pixel-styled sidebar workspace with real Cash/Bank filtering.

## Install

```bash
cd frappe-bench
git clone <your-repo-url> apps/cash_and_bank   # or copy the extracted folder there
./env/bin/pip install -e apps/cash_and_bank
bench --site your-site.local install-app cash_and_bank   # first time only
bench --site your-site.local migrate
bench build --app cash_and_bank
sudo supervisorctl restart all   # or restart however your bench serves requests
```

## What's included

- **Approval for Payment** (submittable DocType) — supplier, payable
  account, invoice, purchase-order reference rows, documents-attached
  checklist, payment mode toggle, and live tax/deduction totals
  (Sales Tax → Total Value → I.Tax/S.Tax Withheld → Net Payment),
  computed identically on the client (preview) and server (source of truth).
- **Create → Payment Entry** button on a submitted Approval for Payment,
  mapping into ERPNext's real Payment Entry.
- **Create → Cheque** button (Bank-mode approvals only) that opens a
  **Write Cheque** wizard — Pay To The Order Of, Amount with a live
  "amount in words" preview, Bank A/c No, Title, A/c Payees Only, Amount
  Not Greater Then — modelled on the legacy Cheque Register screen.
  Confirming it creates a real **Cheque** record and opens it in Frappe's
  print view, whose own Print/PDF button is the "Cheque Print" action.
- **Cheque** DocType — the Cheque Register, linked back to its Approval
  for Payment, with a status (Draft/Printed/Issued/Cleared/Cancelled).
- **Real Cash/Bank filtering** — a `custom_mode_of_payment_type` field is
  kept in sync on every Payment Entry with its Mode of Payment's `type`
  (Cash/Bank/General), so "Cash Payments" / "Bank Payments" / "Cash
  Receipts" / "Bank Receipts" in the sidebar are genuinely filtered lists,
  not decoration. Existing Payment Entries are backfilled during
  `bench migrate`.
- **Cash & Bank sidebar** — installed as a Frappe **Custom HTML Block**
  embedded in the "Cash and Bank" workspace: same groups (Payments /
  Receipts / Masters / Reconciliation / Banking / Cheque Register), same
  colored dots, same quick actions as the original mockup, every click
  wired to a real filtered ERPNext list.

## If the sidebar block doesn't appear automatically

The block-install step is deliberately fail-safe (it never blocks
`bench migrate`, since Custom HTML Block's schema can vary by version).
If it doesn't show up:
1. Open the **Cash and Bank** workspace → **Edit** → **Add Block** →
   **Custom Block**.
2. Search for **"Cash and Bank Sidebar"** and insert it.
3. Save the workspace layout.

## Notes

- `Mode of Payment` records for Cash / Meezan Bank / HBL / Bank Transfer /
  Cheque are exported as fixtures.
- Reconciliation/Banking sidebar items point at ERPNext's own Pages —
  `bank-reconciliation`, `bank-reconciliation-tool`, `payment-reconciliation`,
  `bank-statement-import` — double check these route names against your
  ERPNext version; they've moved around across releases.

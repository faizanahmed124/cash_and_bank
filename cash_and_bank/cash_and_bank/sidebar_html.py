SIDEBAR_BLOCK_NAME = "Cash and Bank Sidebar"


def get_sidebar_style():
	return """
#cb-sidebar-root{
  --cb-blue:#2490ef; --cb-blue-dark:#1a68b0; --cb-blue-50:#eef6fd;
  --cb-ink:#1c2733; --cb-ink-soft:#5a6b7b; --cb-line-soft:#e9edf1;
  --cb-cash:#1a7f4b; --cb-bank:#2490ef;
  font-family: var(--font-stack, 'Inter', system-ui, -apple-system, sans-serif);
  background:#fff; border:1px solid var(--cb-line-soft); border-radius:8px;
  max-width:290px; padding:0; font-size:13px; color:var(--cb-ink);
}
#cb-sidebar-root .cb-header{ padding:16px 18px 12px; border-bottom:1px solid var(--cb-line-soft);
  display:flex; align-items:center; gap:10px; }
#cb-sidebar-root .cb-icon{ width:30px; height:30px; border-radius:7px;
  background:linear-gradient(135deg,var(--cb-blue),var(--cb-blue-dark));
  display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:14px; flex-shrink:0;}
#cb-sidebar-root .cb-name{ font-weight:700; font-size:14.5px; letter-spacing:-.01em;}
#cb-sidebar-root .cb-sub{ font-size:10.5px; color:var(--cb-ink-soft); margin-top:1px;}
#cb-sidebar-root .cb-scroll{ padding:10px 10px 16px; }
#cb-sidebar-root .cb-quick{ display:flex; flex-direction:column; gap:6px; padding:2px 4px 14px;
  border-bottom:1px solid var(--cb-line-soft); margin-bottom:10px;}
#cb-sidebar-root .cb-qa{ display:flex; align-items:center; gap:8px; background:var(--cb-blue-50);
  color:var(--cb-blue-dark); border:1px dashed #b9dbf7; border-radius:6px; padding:7px 10px;
  font-size:12px; font-weight:600; cursor:pointer; transition:.12s;}
#cb-sidebar-root .cb-qa:hover{ background:#dff0fd; }
#cb-sidebar-root .cb-group{ margin-bottom:4px; }
#cb-sidebar-root .cb-group-label{ font-size:10.5px; font-weight:700; letter-spacing:.06em;
  color:#8b9aa8; text-transform:uppercase; padding:10px 10px 4px;}
#cb-sidebar-root .cb-item{ display:flex; align-items:center; gap:8px; padding:6.5px 10px 6.5px 12px;
  border-radius:6px; cursor:pointer; font-size:12.6px; font-weight:500; margin:1px 2px;
  transition:.1s; position:relative;}
#cb-sidebar-root .cb-item:hover{ background:#f1f4f7; }
#cb-sidebar-root .cb-item.active{ background:var(--cb-blue-50); color:var(--cb-blue-dark); font-weight:600;}
#cb-sidebar-root .cb-item.active::before{ content:""; position:absolute; left:0; top:6px; bottom:6px;
  width:3px; background:var(--cb-blue); border-radius:0 3px 3px 0;}
#cb-sidebar-root .cb-dot{ width:6px; height:6px; border-radius:50%; flex-shrink:0;}
#cb-sidebar-root .cb-dot-cash{ background:var(--cb-cash);}
#cb-sidebar-root .cb-dot-bank{ background:var(--cb-bank);}
#cb-sidebar-root .cb-dot-neutral{ background:#9fb0bd;}
"""


def get_sidebar_html():
	"""Returns just the markup (no <style>/<script> tags — those are kept
	separate because Custom HTML Block renders html/style/script through
	frappe.create_shadow_element(wrapper, html, style, script) as three
	distinct fields, not one combined blob)."""
	return """
<div id="cb-sidebar-root">
  <div class="cb-header">
    <div class="cb-icon">C&amp;B</div>
    <div>
      <div class="cb-name">Cash &amp; Bank</div>
      <div class="cb-sub" id="cb-company-sub">&nbsp;</div>
    </div>
  </div>
  <div class="cb-scroll">
    <div class="cb-quick">
      <div class="cb-qa" data-action="new-afp">＋ New Approval for Payment</div>
      <div class="cb-qa" data-action="list-afp">📄 Approval for Payment List</div>
    </div>

    <div class="cb-group">
      <div class="cb-group-label">Payments</div>
      <div class="cb-item" data-dt="Payment Entry" data-filters='{"payment_type":"Pay","custom_mode_of_payment_type":"Cash"}'>
        <span class="cb-dot cb-dot-cash"></span>Cash Payments</div>
      <div class="cb-item" data-dt="Payment Entry" data-filters='{"payment_type":"Pay","custom_mode_of_payment_type":"Bank"}'>
        <span class="cb-dot cb-dot-bank"></span>Bank Payments</div>
      <div class="cb-item" data-dt="Payment Entry" data-filters='{"payment_type":"Pay","party_type":"Supplier"}'>
        <span class="cb-dot cb-dot-neutral"></span>Supplier Payments</div>
      <div class="cb-item" data-dt="Payment Entry" data-filters='{"payment_type":"Receive","party_type":"Customer"}'>
        <span class="cb-dot cb-dot-neutral"></span>Customer Receipts</div>
    </div>

    <div class="cb-group">
      <div class="cb-group-label">Receipts</div>
      <div class="cb-item" data-dt="Payment Entry" data-filters='{"payment_type":"Receive","custom_mode_of_payment_type":"Cash"}'>
        <span class="cb-dot cb-dot-cash"></span>Cash Receipts</div>
      <div class="cb-item" data-dt="Payment Entry" data-filters='{"payment_type":"Receive","custom_mode_of_payment_type":"Bank"}'>
        <span class="cb-dot cb-dot-bank"></span>Bank Receipts</div>
    </div>

    <div class="cb-group">
      <div class="cb-group-label">Masters</div>
      <div class="cb-item" data-dt="Customer">Customers</div>
      <div class="cb-item" data-dt="Supplier">Suppliers</div>
      <div class="cb-item" data-dt="Bank">Banks</div>
      <div class="cb-item" data-dt="Bank Account">Bank Accounts</div>
      <div class="cb-item" data-dt="Mode of Payment">Mode of Payment</div>
    </div>

    <div class="cb-group">
      <div class="cb-group-label">Reconciliation</div>
      <div class="cb-item" data-page="bank-reconciliation">Bank Reconciliation</div>
      <div class="cb-item" data-page="bank-reconciliation-tool">Bank Reconciliation Tool</div>
      <div class="cb-item" data-page="payment-reconciliation">Payment Reconciliation</div>
    </div>

    <div class="cb-group">
      <div class="cb-group-label">Banking</div>
      <div class="cb-item" data-dt="Bank Transaction">Bank Transactions</div>
      <div class="cb-item" data-page="bank-statement-import">Bank Statement Import</div>
      <div class="cb-item" data-dt="Bank Clearance">Bank Clearance</div>
      <div class="cb-item" data-dt="Bank Guarantee">Bank Guarantee</div>
      <div class="cb-item" data-dt="Invoice Discounting">Invoice Discounting</div>
      <div class="cb-item" data-dt="Cheque">Cheque Register</div>
    </div>
  </div>
</div>
"""


def get_sidebar_script():
	return """
(function(){
  var root = document.getElementById('cb-sidebar-root');
  if(!root) return;

  frappe.db.get_value('Company', frappe.defaults.get_default('company'), 'company_name').then(function(r){
    var el = document.getElementById('cb-company-sub');
    if(el && r && r.message) el.textContent = r.message.company_name || '';
  });

  function setActive(el){
    root.querySelectorAll('.cb-item').forEach(function(n){ n.classList.remove('active'); });
    el.classList.add('active');
  }

  root.querySelectorAll('[data-action]').forEach(function(el){
    el.addEventListener('click', function(){
      var action = el.getAttribute('data-action');
      if(action === 'new-afp'){ frappe.new_doc('Approval for Payment'); }
      if(action === 'list-afp'){ frappe.set_route('List', 'Approval for Payment'); }
    });
  });

  root.querySelectorAll('.cb-item').forEach(function(el){
    el.addEventListener('click', function(){
      setActive(el);
      var dt = el.getAttribute('data-dt');
      var page = el.getAttribute('data-page');
      if(page){
        frappe.set_route(page);
        return;
      }
      if(dt){
        var filtersAttr = el.getAttribute('data-filters');
        var filters = filtersAttr ? JSON.parse(filtersAttr) : {};
        frappe.route_options = filters;
        frappe.set_route('List', dt, 'List');
      }
    });
  });
})();
"""

import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";

const BLANK_LINE = () => ({ description: "", quantity: 1, unit_price: 0, account_id: "", item_id: "" });

export default function BillDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { hasModule } = useAuth();

  const [bill, setBill] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [items, setItems] = useState([]);
  const [vendorId, setVendorId] = useState(searchParams.get("vendor_id") || "");
  const [billNumber, setBillNumber] = useState("");
  const [lines, setLines] = useState([BLANK_LINE()]);
  const [taxRate, setTaxRate] = useState(0);
  const [memo, setMemo] = useState("");
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const projectManagerEnabled = hasModule("project_manager");

  useEffect(() => {
    client.get("/accounts").then((res) => setAccounts(res.data.accounts.filter((a) => a.type === "expense")));
    if (hasModule("inventory")) {
      client.get("/items").then((res) => setItems(res.data.items.filter((i) => i.is_active)));
    }
    if (projectManagerEnabled) {
      client.get("/projects").then((res) => setProjects(res.data.projects));
    }

    if (isNew) {
      setBill(null);
      setLoading(false);
      client.get("/vendors").then((res) => setVendors(res.data.vendors));
      return;
    }
    setLoading(true);
    client.get(`/bills/${id}`).then((res) => {
      const b = res.data.bill;
      setBill(b);
      setBillNumber(b.bill_number || "");
      setLines(b.lines.length ? b.lines : [BLANK_LINE()]);
      setMemo(b.memo || "");
      setProjectId(b.project_id || "");
      setLoading(false);
    });
  }, [id, isNew]);

  function updateLine(idx, field, value) {
    setLines((ls) => ls.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));
  }
  function applyItem(idx, itemId) {
    const item = items.find((i) => i.id === itemId);
    setLines((ls) => ls.map((l, i) => {
      if (i !== idx) return l;
      if (!item) return { ...l, item_id: "" };
      return {
        ...l,
        item_id: item.id,
        description: l.description || item.name,
        unit_price: item.unit_cost,
        account_id: l.account_id || item.expense_account_id || "",
      };
    }));
  }
  function addLine() {
    setLines((ls) => [...ls, BLANK_LINE()]);
  }
  function removeLine(idx) {
    setLines((ls) => ls.filter((_, i) => i !== idx));
  }

  const subtotal = lines.reduce((sum, l) => sum + (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0), 0);
  const taxTotal = subtotal * (parseFloat(taxRate) || 0);
  const total = subtotal + taxTotal;

  async function handleSave(e) {
    e.preventDefault();
    setError("");
    if (isNew && !vendorId) {
      setError("Please select a vendor");
      return;
    }
    setSaving(true);
    try {
      const payload = { lines, memo, tax_rate: taxRate, bill_number: billNumber };
      if (projectManagerEnabled) payload.project_id = projectId || null;
      if (isNew) {
        payload.vendor_id = vendorId;
        const res = await client.post("/bills", payload);
        navigate(`/bills/${res.data.bill.id}`);
      } else {
        const res = await client.patch(`/bills/${id}`, payload);
        setBill(res.data.bill);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmitForApproval() {
    const res = await client.post(`/bills/${id}/submit`);
    setBill(res.data.bill);
  }
  async function handleApprove() {
    const res = await client.post(`/bills/${id}/approve`);
    setBill(res.data.bill);
  }
  async function handleVoid() {
    if (!confirm("Void this bill? This cannot be undone.")) return;
    const res = await client.post(`/bills/${id}/void`);
    setBill(res.data.bill);
  }

  if (loading || (!isNew && !bill)) return <div className="page-loading">Loading...</div>;

  const editable = isNew || bill?.status === "draft";

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New Bill" : (bill.bill_number || `Bill ${bill.id.slice(0, 8)}`)}</h1>
        <div className="button-row">
          {!isNew && bill.status === "draft" && (
            <button className="btn-secondary" onClick={handleSubmitForApproval}>Submit for Approval</button>
          )}
          {!isNew && bill.status === "pending_approval" && (
            <button className="btn-primary" onClick={handleApprove}>Approve</button>
          )}
          {!isNew && bill.status !== "void" && bill.status !== "paid" && (
            <button className="btn-danger" onClick={handleVoid}>Void</button>
          )}
          {!isNew && (bill.status === "approved" || bill.status === "partial") && bill.balance_due !== "0.00" && (
            <Link className="btn-primary" to={`/vendor-payments/new?vendor_id=${bill.vendor_id}&bill_id=${id}`}>
              Pay Bill
            </Link>
          )}
        </div>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {!isNew && <span className={`badge badge-${bill.status}`}>{bill.status.replace(/_/g, " ")}</span>}

      <form className="card" onSubmit={handleSave}>
        {isNew && (
          <label>
            Vendor *
            <select value={vendorId} onChange={(e) => setVendorId(e.target.value)} required>
              <option value="">Select a vendor...</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>{v.display_name}</option>
              ))}
            </select>
          </label>
        )}

        <label>
          Vendor's Bill/Invoice #
          <input value={billNumber} disabled={!editable} onChange={(e) => setBillNumber(e.target.value)} />
        </label>

        {projectManagerEnabled && (
          <label>
            Project (optional)
            <select value={projectId} disabled={!editable} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">No project</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.project_number} - {p.name}</option>)}
            </select>
          </label>
        )}

        <table className="data-table line-items">
          <thead>
            <tr>
              {items.length > 0 && <th>Item</th>}
              <th>Description</th><th>GL Account</th><th>Qty</th><th>Unit Price</th><th>Amount</th>{editable && <th></th>}
            </tr>
          </thead>
          <tbody>
            {lines.map((l, idx) => (
              <tr key={idx}>
                {items.length > 0 && (
                  <td>
                    <select
                      value={l.item_id || ""}
                      disabled={!editable}
                      onChange={(e) => applyItem(idx, e.target.value)}
                    >
                      <option value="">Custom line</option>
                      {items.map((it) => (
                        <option key={it.id} value={it.id}>{it.sku} - {it.name}</option>
                      ))}
                    </select>
                  </td>
                )}
                <td>
                  <input
                    value={l.description}
                    disabled={!editable}
                    onChange={(e) => updateLine(idx, "description", e.target.value)}
                    placeholder="Description"
                  />
                </td>
                <td>
                  <select
                    value={l.account_id || ""}
                    disabled={!editable}
                    onChange={(e) => updateLine(idx, "account_id", e.target.value)}
                  >
                    <option value="">Uncategorized</option>
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>{a.code} {a.name}</option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    type="number" step="0.01" value={l.quantity} disabled={!editable}
                    onChange={(e) => updateLine(idx, "quantity", e.target.value)}
                    style={{ width: "70px" }}
                  />
                </td>
                <td>
                  <input
                    type="number" step="0.01" value={l.unit_price} disabled={!editable}
                    onChange={(e) => updateLine(idx, "unit_price", e.target.value)}
                    style={{ width: "90px" }}
                  />
                </td>
                <td>${((parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0)).toFixed(2)}</td>
                {editable && <td><button type="button" className="btn-link" onClick={() => removeLine(idx)}>Remove</button></td>}
              </tr>
            ))}
          </tbody>
        </table>

        {editable && <button type="button" className="btn-secondary" onClick={addLine}>Add Line</button>}

        <div className="invoice-totals">
          <label>
            Tax Rate (e.g. 0.08 for 8%)
            <input type="number" step="0.001" value={taxRate} disabled={!editable} onChange={(e) => setTaxRate(e.target.value)} style={{ width: "100px" }} />
          </label>
          <div>Subtotal: ${subtotal.toFixed(2)}</div>
          <div>Tax: ${taxTotal.toFixed(2)}</div>
          <div className="total-line">Total: ${total.toFixed(2)}</div>
          {!isNew && <div className="total-line">Balance Due: ${bill.balance_due}</div>}
        </div>

        <label>
          Memo
          <textarea value={memo} disabled={!editable} onChange={(e) => setMemo(e.target.value)} rows={2} />
        </label>

        {editable && (
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving..." : isNew ? "Create Bill" : "Save Changes"}
          </button>
        )}
      </form>
    </div>
  );
}

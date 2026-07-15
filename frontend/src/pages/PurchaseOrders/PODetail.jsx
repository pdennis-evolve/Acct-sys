import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
import client from "../../api/client";

const BLANK_LINE = () => ({ description: "", quantity: 1, unit_price: 0, account_id: "" });

export default function PODetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [po, setPo] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [vendorId, setVendorId] = useState(searchParams.get("vendor_id") || "");
  const [expectedDate, setExpectedDate] = useState("");
  const [lines, setLines] = useState([BLANK_LINE()]);
  const [memo, setMemo] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    client.get("/accounts").then((res) => setAccounts(res.data.accounts.filter((a) => a.type === "expense")));

    if (isNew) {
      setPo(null);
      setLoading(false);
      client.get("/vendors").then((res) => setVendors(res.data.vendors));
      return;
    }
    setLoading(true);
    client.get(`/purchase-orders/${id}`).then((res) => {
      const p = res.data.purchase_order;
      setPo(p);
      setExpectedDate(p.expected_date || "");
      setLines(p.lines.length ? p.lines : [BLANK_LINE()]);
      setMemo(p.memo || "");
      setLoading(false);
    });
  }, [id, isNew]);

  function updateLine(idx, field, value) {
    setLines((ls) => ls.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));
  }
  function addLine() {
    setLines((ls) => [...ls, BLANK_LINE()]);
  }
  function removeLine(idx) {
    setLines((ls) => ls.filter((_, i) => i !== idx));
  }

  const subtotal = lines.reduce((sum, l) => sum + (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0), 0);

  async function handleSave(e) {
    e.preventDefault();
    setError("");
    if (isNew && !vendorId) {
      setError("Please select a vendor");
      return;
    }
    setSaving(true);
    try {
      const payload = { lines, memo, expected_date: expectedDate || null };
      if (isNew) {
        payload.vendor_id = vendorId;
        const res = await client.post("/purchase-orders", payload);
        navigate(`/purchase-orders/${res.data.purchase_order.id}`);
      } else {
        const res = await client.patch(`/purchase-orders/${id}`, payload);
        setPo(res.data.purchase_order);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSend() {
    const res = await client.post(`/purchase-orders/${id}/send`);
    setPo(res.data.purchase_order);
  }
  async function handleReceive() {
    const res = await client.post(`/purchase-orders/${id}/receive`);
    setPo(res.data.purchase_order);
  }
  async function handleCancel() {
    if (!confirm("Cancel this purchase order?")) return;
    const res = await client.post(`/purchase-orders/${id}/cancel`);
    setPo(res.data.purchase_order);
  }
  async function handleConvertToBill() {
    const res = await client.post(`/purchase-orders/${id}/convert-to-bill`);
    navigate(`/bills/${res.data.bill.id}`);
  }

  if (loading || (!isNew && !po)) return <div className="page-loading">Loading...</div>;

  const editable = isNew || po?.status === "draft";

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New Purchase Order" : po.po_number}</h1>
        <div className="button-row">
          {!isNew && po.status === "draft" && <button className="btn-secondary" onClick={handleSend}>Send to Vendor</button>}
          {!isNew && po.status === "sent" && <button className="btn-secondary" onClick={handleReceive}>Mark Received</button>}
          {!isNew && (po.status === "sent" || po.status === "received") && !po.converted_bill_id && (
            <button className="btn-primary" onClick={handleConvertToBill}>Convert to Bill</button>
          )}
          {!isNew && po.status !== "closed" && po.status !== "cancelled" && (
            <button className="btn-danger" onClick={handleCancel}>Cancel</button>
          )}
          {!isNew && po.converted_bill_id && (
            <Link className="btn-secondary" to={`/bills/${po.converted_bill_id}`}>View Bill</Link>
          )}
        </div>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {!isNew && <span className={`badge badge-${po.status}`}>{po.status}</span>}

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
          Expected Delivery Date
          <input type="date" value={expectedDate} disabled={!editable} onChange={(e) => setExpectedDate(e.target.value)} />
        </label>

        <table className="data-table line-items">
          <thead>
            <tr><th>Description</th><th>GL Account</th><th>Qty</th><th>Unit Price</th><th>Amount</th>{editable && <th></th>}</tr>
          </thead>
          <tbody>
            {lines.map((l, idx) => (
              <tr key={idx}>
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
          <div className="total-line">Subtotal: ${subtotal.toFixed(2)}</div>
        </div>

        <label>
          Memo
          <textarea value={memo} disabled={!editable} onChange={(e) => setMemo(e.target.value)} rows={2} />
        </label>

        {editable && (
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving..." : isNew ? "Create Purchase Order" : "Save Changes"}
          </button>
        )}
      </form>
    </div>
  );
}

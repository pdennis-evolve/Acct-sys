import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
import client from "../../api/client";

const BLANK_LINE = () => ({ description: "", quantity: 1, unit_price: 0, account_id: "" });

export default function InvoiceDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [invoice, setInvoice] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [customerId, setCustomerId] = useState(searchParams.get("customer_id") || "");
  const [lines, setLines] = useState([BLANK_LINE()]);
  const [taxRate, setTaxRate] = useState(0);
  const [memo, setMemo] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isNew) {
      setInvoice(null);
      setLoading(false);
      client.get("/customers").then((res) => setCustomers(res.data.customers));
      return;
    }
    setLoading(true);
    client.get(`/invoices/${id}`).then((res) => {
      const inv = res.data.invoice;
      setInvoice(inv);
      setLines(inv.lines.length ? inv.lines : [BLANK_LINE()]);
      setMemo(inv.memo || "");
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
  const taxTotal = subtotal * (parseFloat(taxRate) || 0);
  const total = subtotal + taxTotal;

  async function handleSave(e) {
    e.preventDefault();
    setError("");
    if (isNew && !customerId) {
      setError("Please select a customer");
      return;
    }
    setSaving(true);
    try {
      const payload = { lines, memo, tax_rate: taxRate };
      if (isNew) {
        payload.customer_id = customerId;
        const res = await client.post("/invoices", payload);
        navigate(`/invoices/${res.data.invoice.id}`);
      } else {
        const res = await client.patch(`/invoices/${id}`, payload);
        setInvoice(res.data.invoice);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownloadPdf() {
    const res = await client.get(`/invoices/${id}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function handleSend() {
    const res = await client.post(`/invoices/${id}/send`);
    setInvoice(res.data.invoice);
  }

  async function handleVoid() {
    if (!confirm("Void this invoice? This cannot be undone.")) return;
    const res = await client.post(`/invoices/${id}/void`);
    setInvoice(res.data.invoice);
  }

  if (loading || (!isNew && !invoice)) return <div className="page-loading">Loading...</div>;

  const editable = isNew || invoice?.status === "draft";

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New Invoice" : invoice.invoice_number}</h1>
        <div className="button-row">
          {!isNew && <button type="button" className="btn-secondary" onClick={handleDownloadPdf}>Download PDF</button>}
          {!isNew && invoice.status === "draft" && <button className="btn-secondary" onClick={handleSend}>Send Invoice</button>}
          {!isNew && invoice.status !== "void" && invoice.status !== "paid" && (
            <button className="btn-danger" onClick={handleVoid}>Void</button>
          )}
          {!isNew && invoice.balance_due !== "0.00" && invoice.status !== "void" && (
            <Link className="btn-primary" to={`/payments/new?customer_id=${invoice.customer_id}&invoice_id=${id}`}>
              Record Payment
            </Link>
          )}
        </div>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {!isNew && <span className={`badge badge-${invoice.status}`}>{invoice.status}</span>}

      <form className="card" onSubmit={handleSave}>
        {isNew && (
          <label>
            Customer *
            <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
              <option value="">Select a customer...</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.display_name}</option>
              ))}
            </select>
          </label>
        )}

        <table className="data-table line-items">
          <thead>
            <tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Amount</th>{editable && <th></th>}</tr>
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
          {!isNew && <div className="total-line">Balance Due: ${invoice.balance_due}</div>}
        </div>

        <label>
          Memo
          <textarea value={memo} disabled={!editable} onChange={(e) => setMemo(e.target.value)} rows={2} />
        </label>

        {editable && (
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving..." : isNew ? "Create Invoice" : "Save Changes"}
          </button>
        )}
      </form>
    </div>
  );
}

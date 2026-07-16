import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import ShipmentPanel from "../../components/ShipmentPanel";

const BLANK_LINE = () => ({ description: "", quantity: 1, unit_price: 0, account_id: "", item_id: "" });

export default function InvoiceDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { hasModule } = useAuth();

  const [invoice, setInvoice] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [items, setItems] = useState([]);
  const [taxRates, setTaxRates] = useState([]);
  const [customerId, setCustomerId] = useState(searchParams.get("customer_id") || "");
  const [lines, setLines] = useState([BLANK_LINE()]);
  const [taxRateId, setTaxRateId] = useState("");
  const [memo, setMemo] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [emailing, setEmailing] = useState(false);
  const [emailMessage, setEmailMessage] = useState("");

  useEffect(() => {
    client.get("/accounts").then((res) => setAccounts(res.data.accounts.filter((a) => a.type === "income")));
    if (hasModule("inventory")) {
      client.get("/items").then((res) => setItems(res.data.items.filter((i) => i.is_active)));
    }
    client.get("/tax-rates").then((res) => {
      setTaxRates(res.data.tax_rates);
      if (isNew) {
        const def = res.data.tax_rates.find((r) => r.is_default);
        if (def) setTaxRateId(def.id);
      }
    });

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
      setTaxRateId(inv.tax_rate_id || "");
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
        unit_price: item.unit_price,
        account_id: l.account_id || item.income_account_id || "",
      };
    }));
  }
  function addLine() {
    setLines((ls) => [...ls, BLANK_LINE()]);
  }
  function removeLine(idx) {
    setLines((ls) => ls.filter((_, i) => i !== idx));
  }

  const selectedRatePct = taxRateId ? parseFloat(taxRates.find((r) => r.id === taxRateId)?.rate || 0) : 0;
  const subtotal = lines.reduce((sum, l) => sum + (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0), 0);
  const taxTotal = subtotal * selectedRatePct;
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
      const payload = taxRateId ? { lines, memo, tax_rate_id: taxRateId } : { lines, memo, tax_rate: 0 };
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

  async function handleEmailInvoice() {
    setEmailing(true);
    setEmailMessage("");
    try {
      const res = await client.post(`/invoices/${id}/email`);
      setEmailMessage(`Sent to ${res.data.to} via ${res.data.via === "microsoft" ? "Microsoft 365" : "Google"}.`);
    } catch (err) {
      setEmailMessage(err.response?.data?.error || "Could not send the email.");
    } finally {
      setEmailing(false);
    }
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
          {!isNew && invoice.status !== "draft" && (
            <button type="button" className="btn-secondary" onClick={handleEmailInvoice} disabled={emailing}>
              {emailing ? "Sending..." : "Email Invoice"}
            </button>
          )}
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
      {emailMessage && <div className={emailMessage.startsWith("Sent") ? "auth-success" : "auth-error"}>{emailMessage}</div>}

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
            Tax Rate
            <select value={taxRateId} disabled={!editable} onChange={(e) => setTaxRateId(e.target.value)} style={{ width: "220px" }}>
              <option value="">No Tax</option>
              {taxRates.map((r) => (
                <option key={r.id} value={r.id}>{r.name} ({(parseFloat(r.rate) * 100).toFixed(2)}%)</option>
              ))}
            </select>
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

      {!isNew && hasModule("order_tracking") && (
        <ShipmentPanel referenceType="invoice" referenceId={id} />
      )}
    </div>
  );
}

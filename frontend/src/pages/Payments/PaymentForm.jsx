import { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import client from "../../api/client";

export default function PaymentForm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [customers, setCustomers] = useState([]);
  const [cashAccounts, setCashAccounts] = useState([]);
  const [customerId, setCustomerId] = useState(searchParams.get("customer_id") || "");
  const [openInvoices, setOpenInvoices] = useState([]);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("check");
  const [reference, setReference] = useState("");
  const [cashAccountId, setCashAccountId] = useState("");
  const [applications, setApplications] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    client.get("/customers").then((res) => setCustomers(res.data.customers));
    client.get("/cash-accounts").then((res) => setCashAccounts(res.data.cash_accounts));
  }, []);

  useEffect(() => {
    if (!customerId) {
      setOpenInvoices([]);
      return;
    }
    client.get("/invoices", { params: { customer_id: customerId } }).then((res) => {
      const open = res.data.invoices.filter((i) => parseFloat(i.balance_due) > 0 && i.status !== "void");
      setOpenInvoices(open);
      const preselect = searchParams.get("invoice_id");
      if (preselect) {
        const inv = open.find((i) => i.id === preselect);
        if (inv) setApplications({ [preselect]: inv.balance_due });
      }
    });
  }, [customerId]);

  const totalApplied = Object.values(applications).reduce((sum, v) => sum + (parseFloat(v) || 0), 0);

  function updateApplication(invoiceId, value) {
    setApplications((a) => ({ ...a, [invoiceId]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const applicationsPayload = Object.entries(applications)
        .filter(([, amt]) => parseFloat(amt) > 0)
        .map(([invoice_id, amt]) => ({ invoice_id, amount_applied: amt }));

      const res = await client.post("/payments", {
        customer_id: customerId,
        amount,
        method,
        reference_number: reference,
        cash_account_id: cashAccountId || null,
        applications: applicationsPayload,
      });
      navigate(`/payments`);
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Record Payment</h1>
        <Link to="/payments" className="btn-link">Back to receipts</Link>
      </div>

      {error && <div className="auth-error">{error}</div>}

      <form className="card form-grid" onSubmit={handleSubmit}>
        <label>
          Customer *
          <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
            <option value="">Select a customer...</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>{c.display_name}</option>
            ))}
          </select>
        </label>

        <div className="form-row">
          <label>
            Amount Received *
            <input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </label>
          <label>
            Method
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="check">Check</option>
              <option value="cash">Cash</option>
              <option value="credit_card">Credit Card</option>
              <option value="ach">ACH</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label>
            Reference #
            <input value={reference} onChange={(e) => setReference(e.target.value)} />
          </label>
        </div>

        <label>
          Deposit To
          <select value={cashAccountId} onChange={(e) => setCashAccountId(e.target.value)}>
            <option value="">Undeposited (no register entry)</option>
            {cashAccounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </label>

        {openInvoices.length > 0 && (
          <>
            <h3 className="form-section-title">Apply to Invoices</h3>
            <table className="data-table">
              <thead><tr><th>Invoice</th><th>Balance Due</th><th>Apply Amount</th></tr></thead>
              <tbody>
                {openInvoices.map((inv) => (
                  <tr key={inv.id}>
                    <td>{inv.invoice_number}</td>
                    <td>${inv.balance_due}</td>
                    <td>
                      <input
                        type="number" step="0.01"
                        value={applications[inv.id] || ""}
                        onChange={(e) => updateApplication(inv.id, e.target.value)}
                        style={{ width: "100px" }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="total-line">Total Applied: ${totalApplied.toFixed(2)}</div>
          </>
        )}

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving..." : "Record Payment"}
        </button>
      </form>
    </div>
  );
}

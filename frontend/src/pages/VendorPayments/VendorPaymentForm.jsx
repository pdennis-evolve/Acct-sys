import { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import client from "../../api/client";

export default function VendorPaymentForm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [vendors, setVendors] = useState([]);
  const [cashAccounts, setCashAccounts] = useState([]);
  const [vendorId, setVendorId] = useState(searchParams.get("vendor_id") || "");
  const [payableBills, setPayableBills] = useState([]);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("check");
  const [reference, setReference] = useState("");
  const [cashAccountId, setCashAccountId] = useState("");
  const [applications, setApplications] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    client.get("/vendors").then((res) => setVendors(res.data.vendors));
    client.get("/cash-accounts").then((res) => setCashAccounts(res.data.cash_accounts));
  }, []);

  useEffect(() => {
    if (!vendorId) {
      setPayableBills([]);
      return;
    }
    client.get("/bills", { params: { vendor_id: vendorId } }).then((res) => {
      const payable = res.data.bills.filter(
        (b) => (b.status === "approved" || b.status === "partial") && parseFloat(b.balance_due) > 0
      );
      setPayableBills(payable);
      const preselect = searchParams.get("bill_id");
      if (preselect) {
        const bill = payable.find((b) => b.id === preselect);
        if (bill) setApplications({ [preselect]: bill.balance_due });
      }
    });
  }, [vendorId]);

  const totalApplied = Object.values(applications).reduce((sum, v) => sum + (parseFloat(v) || 0), 0);

  function updateApplication(billId, value) {
    setApplications((a) => ({ ...a, [billId]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const applicationsPayload = Object.entries(applications)
        .filter(([, amt]) => parseFloat(amt) > 0)
        .map(([bill_id, amt]) => ({ bill_id, amount_applied: amt }));

      await client.post("/vendor-payments", {
        vendor_id: vendorId,
        amount,
        method,
        reference_number: reference,
        cash_account_id: cashAccountId || null,
        applications: applicationsPayload,
      });
      navigate("/vendor-payments");
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Pay a Bill</h1>
        <Link to="/vendor-payments" className="btn-link">Back to bill payments</Link>
      </div>

      {error && <div className="auth-error">{error}</div>}

      <form className="card form-grid" onSubmit={handleSubmit}>
        <label>
          Vendor *
          <select value={vendorId} onChange={(e) => setVendorId(e.target.value)} required>
            <option value="">Select a vendor...</option>
            {vendors.map((v) => (
              <option key={v.id} value={v.id}>{v.display_name}</option>
            ))}
          </select>
        </label>

        <div className="form-row">
          <label>
            Amount Paid *
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
          Pay From
          <select value={cashAccountId} onChange={(e) => setCashAccountId(e.target.value)}>
            <option value="">No register entry</option>
            {cashAccounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </label>

        {payableBills.length > 0 && (
          <>
            <h3 className="form-section-title">Apply to Bills</h3>
            <table className="data-table">
              <thead><tr><th>Bill</th><th>Balance Due</th><th>Apply Amount</th></tr></thead>
              <tbody>
                {payableBills.map((bill) => (
                  <tr key={bill.id}>
                    <td>{bill.bill_number || bill.id.slice(0, 8)}</td>
                    <td>${bill.balance_due}</td>
                    <td>
                      <input
                        type="number" step="0.01"
                        value={applications[bill.id] || ""}
                        onChange={(e) => updateApplication(bill.id, e.target.value)}
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
        {vendorId && payableBills.length === 0 && (
          <p className="text-muted">This vendor has no approved bills awaiting payment.</p>
        )}

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving..." : "Record Payment"}
        </button>
      </form>
    </div>
  );
}

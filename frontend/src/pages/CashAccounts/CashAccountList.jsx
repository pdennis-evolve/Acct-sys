import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

export default function CashAccountList() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", account_type: "checking", bank_name: "", opening_balance: 0 });
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/cash-accounts").then((res) => setAccounts(res.data.cash_accounts)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/cash-accounts", form);
      setForm({ name: "", account_type: "checking", bank_name: "", opening_balance: 0 });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Check Register</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New Account"}
        </button>
      </div>

      {showForm && (
        <form className="card form-grid" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="form-row">
            <label>
              Name *
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </label>
            <label>
              Type
              <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })}>
                <option value="checking">Checking</option>
                <option value="savings">Savings</option>
                <option value="cash">Cash</option>
                <option value="credit_card">Credit Card</option>
              </select>
            </label>
            <label>
              Bank Name
              <input value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} />
            </label>
            <label>
              Opening Balance
              <input type="number" step="0.01" value={form.opening_balance} onChange={(e) => setForm({ ...form, opening_balance: e.target.value })} />
            </label>
          </div>
          <button type="submit" className="btn-primary">Create Account</button>
        </form>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead><tr><th>Name</th><th>Type</th><th>Bank</th><th>Balance</th></tr></thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id}>
                <td><Link to={`/cash-accounts/${a.id}`}>{a.name}</Link></td>
                <td>{a.account_type}</td>
                <td>{a.bank_name || "-"}</td>
                <td>${a.current_balance}</td>
              </tr>
            ))}
            {accounts.length === 0 && <tr><td colSpan={4} className="empty-row">No cash accounts yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

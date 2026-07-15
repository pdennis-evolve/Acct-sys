import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import client from "../../api/client";

export default function Register() {
  const { id } = useParams();
  const [account, setAccount] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ txn_type: "withdrawal", amount: "", payee: "", memo: "", check_number: "" });
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get(`/cash-accounts/${id}/register`).then((res) => {
      setAccount(res.data.cash_account);
      setTransactions(res.data.transactions);
    }).finally(() => setLoading(false));
  }

  useEffect(load, [id]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post(`/cash-accounts/${id}/register`, form);
      setForm({ txn_type: "withdrawal", amount: "", payee: "", memo: "", check_number: "" });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    }
  }

  if (loading) return <div className="page-loading">Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h1>{account?.name}</h1>
        <div className="button-row">
          <Link to="/cash-accounts" className="btn-link">Back to accounts</Link>
          <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "New Entry"}
          </button>
        </div>
      </div>

      <div className="stat-card" style={{ maxWidth: "260px", marginBottom: "1.5rem" }}>
        <div className="stat-value">${account?.current_balance}</div>
        <div className="stat-label">Current Balance</div>
      </div>

      {showForm && (
        <form className="card form-grid" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="form-row">
            <label>
              Type
              <select value={form.txn_type} onChange={(e) => setForm({ ...form, txn_type: e.target.value })}>
                <option value="deposit">Deposit</option>
                <option value="withdrawal">Withdrawal</option>
                <option value="check">Check</option>
              </select>
            </label>
            <label>
              Amount *
              <input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
            </label>
            <label>
              Payee
              <input value={form.payee} onChange={(e) => setForm({ ...form, payee: e.target.value })} />
            </label>
            {form.txn_type === "check" && (
              <label>
                Check #
                <input value={form.check_number} onChange={(e) => setForm({ ...form, check_number: e.target.value })} />
              </label>
            )}
          </div>
          <label>
            Memo
            <input value={form.memo} onChange={(e) => setForm({ ...form, memo: e.target.value })} />
          </label>
          <button type="submit" className="btn-primary">Add Entry</button>
        </form>
      )}

      <table className="data-table">
        <thead><tr><th>Date</th><th>Type</th><th>Payee</th><th>Check #</th><th>Memo</th><th>Amount</th></tr></thead>
        <tbody>
          {transactions.map((t) => (
            <tr key={t.id}>
              <td>{t.txn_date}</td>
              <td>{t.txn_type}</td>
              <td>{t.payee || "-"}</td>
              <td>{t.check_number || "-"}</td>
              <td>{t.memo || "-"}</td>
              <td className={t.txn_type === "deposit" ? "amount-positive" : "amount-negative"}>
                {t.txn_type === "deposit" ? "+" : "-"}${t.amount}
              </td>
            </tr>
          ))}
          {transactions.length === 0 && <tr><td colSpan={6} className="empty-row">No transactions yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

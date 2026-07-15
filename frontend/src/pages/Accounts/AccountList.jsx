import { useEffect, useState } from "react";
import client from "../../api/client";

const TYPES = ["asset", "liability", "equity", "income", "expense"];

export default function AccountList() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", type: "asset", subtype: "" });
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/accounts").then((res) => setAccounts(res.data.accounts)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/accounts", form);
      setForm({ code: "", name: "", type: "asset", subtype: "" });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    }
  }

  const grouped = TYPES.map((t) => ({ type: t, accounts: accounts.filter((a) => a.type === t) }));

  return (
    <div>
      <div className="page-header">
        <h1>Chart of Accounts</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New Account"}
        </button>
      </div>

      {showForm && (
        <form className="card form-grid" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="form-row">
            <label>
              Code *
              <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required />
            </label>
            <label>
              Name *
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </label>
            <label>
              Type *
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <label>
              Subtype
              <input value={form.subtype} onChange={(e) => setForm({ ...form, subtype: e.target.value })} />
            </label>
          </div>
          <button type="submit" className="btn-primary">Create Account</button>
        </form>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        grouped.map((g) => (
          <div className="card" key={g.type}>
            <h2 className="section-title-cap">{g.type}</h2>
            <table className="data-table">
              <thead><tr><th>Code</th><th>Name</th><th>Subtype</th><th>Status</th></tr></thead>
              <tbody>
                {g.accounts.map((a) => (
                  <tr key={a.id}>
                    <td>{a.code}</td>
                    <td>{a.name}</td>
                    <td>{a.subtype || "-"}</td>
                    <td><span className={`badge ${a.is_active ? "badge-active" : "badge-inactive"}`}>{a.is_active ? "Active" : "Inactive"}</span></td>
                  </tr>
                ))}
                {g.accounts.length === 0 && <tr><td colSpan={4} className="empty-row">No accounts</td></tr>}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  );
}

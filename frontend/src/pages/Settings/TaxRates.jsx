import { useEffect, useState } from "react";
import client from "../../api/client";

export default function TaxRates() {
  const [rates, setRates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", rate: "", jurisdiction: "", is_default: false });
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/tax-rates").then((res) => setRates(res.data.tax_rates)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/tax-rates", form);
      setForm({ name: "", rate: "", jurisdiction: "", is_default: false });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    }
  }

  async function toggleActive(rate) {
    await client.patch(`/tax-rates/${rate.id}`, { is_active: !rate.is_active });
    load();
  }

  async function makeDefault(rate) {
    await client.patch(`/tax-rates/${rate.id}`, { is_default: true });
    load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>Tax Rates</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New Tax Rate"}
        </button>
      </div>
      <p className="text-muted">
        The default rate auto-applies to new invoices. Rates are snapshotted onto each invoice at
        creation time, so editing a rate here never changes historical sales tax reports.
      </p>

      {showForm && (
        <form className="card form-grid" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="form-row">
            <label>
              Name *
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="State Sales Tax" />
            </label>
            <label>
              Rate * (e.g. 0.07 for 7%)
              <input type="number" step="0.0001" value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} required />
            </label>
            <label>
              Jurisdiction
              <input value={form.jurisdiction} onChange={(e) => setForm({ ...form, jurisdiction: e.target.value })} placeholder="Illinois" />
            </label>
          </div>
          <label className="module-toggle">
            <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
            Set as default rate
          </label>
          <button type="submit" className="btn-primary">Create Tax Rate</button>
        </form>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead><tr><th>Name</th><th>Rate</th><th>Jurisdiction</th><th>Default</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {rates.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{(parseFloat(r.rate) * 100).toFixed(2)}%</td>
                <td>{r.jurisdiction || "-"}</td>
                <td>{r.is_default ? <span className="badge badge-active">Default</span> : (
                  <button className="btn-link" onClick={() => makeDefault(r)}>Make default</button>
                )}</td>
                <td><span className={`badge ${r.is_active ? "badge-active" : "badge-inactive"}`}>{r.is_active ? "Active" : "Inactive"}</span></td>
                <td><button className="btn-link" onClick={() => toggleActive(r)}>{r.is_active ? "Deactivate" : "Activate"}</button></td>
              </tr>
            ))}
            {rates.length === 0 && <tr><td colSpan={6} className="empty-row">No tax rates configured.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

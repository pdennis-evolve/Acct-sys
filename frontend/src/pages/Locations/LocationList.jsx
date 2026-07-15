import { useEffect, useState } from "react";
import client from "../../api/client";

export default function LocationList() {
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", address_line1: "", city: "", state: "", postal_code: "", is_default: false });
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/locations").then((res) => setLocations(res.data.locations)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/locations", form);
      setForm({ name: "", address_line1: "", city: "", state: "", postal_code: "", is_default: false });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    }
  }

  async function makeDefault(loc) {
    await client.patch(`/locations/${loc.id}`, { is_default: true });
    load();
  }

  async function toggleActive(loc) {
    await client.patch(`/locations/${loc.id}`, { is_active: !loc.is_active });
    load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>Locations</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New Location"}
        </button>
      </div>
      <p className="text-muted">Stock levels and reorder points are tracked per location.</p>

      {showForm && (
        <form className="card form-grid" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="form-row">
            <label>
              Name *
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </label>
            <label>
              City
              <input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
            </label>
            <label>
              State
              <input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} />
            </label>
          </div>
          <label className="module-toggle">
            <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
            Set as default location
          </label>
          <button type="submit" className="btn-primary">Create Location</button>
        </form>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead><tr><th>Name</th><th>City</th><th>State</th><th>Default</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {locations.map((l) => (
              <tr key={l.id}>
                <td>{l.name}</td>
                <td>{l.city || "-"}</td>
                <td>{l.state || "-"}</td>
                <td>{l.is_default ? <span className="badge badge-active">Default</span> : (
                  <button className="btn-link" onClick={() => makeDefault(l)}>Make default</button>
                )}</td>
                <td><span className={`badge ${l.is_active ? "badge-active" : "badge-inactive"}`}>{l.is_active ? "Active" : "Inactive"}</span></td>
                <td><button className="btn-link" onClick={() => toggleActive(l)}>{l.is_active ? "Deactivate" : "Activate"}</button></td>
              </tr>
            ))}
            {locations.length === 0 && <tr><td colSpan={6} className="empty-row">No locations yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

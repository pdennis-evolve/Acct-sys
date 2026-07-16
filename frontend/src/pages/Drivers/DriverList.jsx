import { useEffect, useState } from "react";
import client from "../../api/client";

const STATUSES = ["active", "on_leave", "inactive"];

export default function DriverList() {
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ full_name: "", phone: "", email: "", license_number: "", license_class: "" });
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/drivers").then((res) => setDrivers(res.data.drivers)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/drivers", form);
      setForm({ full_name: "", phone: "", email: "", license_number: "", license_class: "" });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    }
  }

  async function updateStatus(driver, status) {
    await client.patch(`/drivers/${driver.id}`, { status });
    load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>Drivers</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New Driver"}
        </button>
      </div>

      {showForm && (
        <form className="card form-grid" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="form-row">
            <label>
              Full Name *
              <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
            </label>
            <label>
              Phone
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </label>
            <label>
              Email
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </label>
          </div>
          <div className="form-row">
            <label>
              License Number
              <input value={form.license_number} onChange={(e) => setForm({ ...form, license_number: e.target.value })} />
            </label>
            <label>
              License Class
              <input value={form.license_class} onChange={(e) => setForm({ ...form, license_class: e.target.value })} placeholder="CDL-A" />
            </label>
          </div>
          <button type="submit" className="btn-primary">Create Driver</button>
        </form>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead><tr><th>Name</th><th>Phone</th><th>License #</th><th>Class</th><th>Status</th></tr></thead>
          <tbody>
            {drivers.map((d) => (
              <tr key={d.id}>
                <td>{d.full_name}</td>
                <td>{d.phone || "-"}</td>
                <td>{d.license_number || "-"}</td>
                <td>{d.license_class || "-"}</td>
                <td>
                  <select value={d.status} onChange={(e) => updateStatus(d, e.target.value)}>
                    {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                  </select>
                </td>
              </tr>
            ))}
            {drivers.length === 0 && <tr><td colSpan={5} className="empty-row">No drivers yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

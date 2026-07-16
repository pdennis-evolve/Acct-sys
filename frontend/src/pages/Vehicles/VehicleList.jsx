import { useEffect, useState } from "react";
import client from "../../api/client";

const TYPES = ["truck", "van", "trailer", "other"];
const STATUSES = ["active", "maintenance", "out_of_service"];

export default function VehicleList() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ unit_number: "", vehicle_type: "truck", make: "", model: "", year: "", license_plate: "" });
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/vehicles").then((res) => setVehicles(res.data.vehicles)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/vehicles", form);
      setForm({ unit_number: "", vehicle_type: "truck", make: "", model: "", year: "", license_plate: "" });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    }
  }

  async function updateStatus(vehicle, status) {
    await client.patch(`/vehicles/${vehicle.id}`, { status });
    load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>Vehicles</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New Vehicle"}
        </button>
      </div>

      {showForm && (
        <form className="card form-grid" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="form-row">
            <label>
              Unit Number *
              <input value={form.unit_number} onChange={(e) => setForm({ ...form, unit_number: e.target.value })} required />
            </label>
            <label>
              Type
              <select value={form.vehicle_type} onChange={(e) => setForm({ ...form, vehicle_type: e.target.value })}>
                {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <label>
              Year
              <input type="number" value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} />
            </label>
          </div>
          <div className="form-row">
            <label>
              Make
              <input value={form.make} onChange={(e) => setForm({ ...form, make: e.target.value })} />
            </label>
            <label>
              Model
              <input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} />
            </label>
            <label>
              License Plate
              <input value={form.license_plate} onChange={(e) => setForm({ ...form, license_plate: e.target.value })} />
            </label>
          </div>
          <button type="submit" className="btn-primary">Create Vehicle</button>
        </form>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead><tr><th>Unit #</th><th>Type</th><th>Make/Model</th><th>Year</th><th>Plate</th><th>Status</th></tr></thead>
          <tbody>
            {vehicles.map((v) => (
              <tr key={v.id}>
                <td>{v.unit_number}</td>
                <td>{v.vehicle_type}</td>
                <td>{[v.make, v.model].filter(Boolean).join(" ") || "-"}</td>
                <td>{v.year || "-"}</td>
                <td>{v.license_plate || "-"}</td>
                <td>
                  <select value={v.status} onChange={(e) => updateStatus(v, e.target.value)}>
                    {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                  </select>
                </td>
              </tr>
            ))}
            {vehicles.length === 0 && <tr><td colSpan={6} className="empty-row">No vehicles yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import client from "../api/client";

const STATUSES = ["pending", "in_transit", "out_for_delivery", "delivered", "exception", "unknown"];

export default function ShipmentPanel({ referenceType, referenceId }) {
  const [shipments, setShipments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [trackingNumber, setTrackingNumber] = useState("");
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/shipments", { params: { reference_type: referenceType, reference_id: referenceId } })
      .then((res) => setShipments(res.data.shipments))
      .finally(() => setLoading(false));
  }

  useEffect(load, [referenceType, referenceId]);

  async function handleAdd(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/shipments", { reference_type: referenceType, reference_id: referenceId, tracking_number: trackingNumber });
      setTrackingNumber("");
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    }
  }

  async function updateStatus(shipment, status) {
    await client.patch(`/shipments/${shipment.id}`, { status });
    load();
  }

  async function refresh(shipment) {
    const res = await client.post(`/shipments/${shipment.id}/refresh`);
    if (!res.data.polled) {
      alert(res.data.shipment.status_note);
    }
    load();
  }

  async function remove(shipment) {
    if (!confirm(`Remove tracking number ${shipment.tracking_number}?`)) return;
    await client.delete(`/shipments/${shipment.id}`);
    load();
  }

  return (
    <div className="card">
      <div className="page-header">
        <h2>Order Tracking</h2>
        <button type="button" className="btn-secondary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "Add Tracking Number"}
        </button>
      </div>

      {showForm && (
        <form className="form-row" onSubmit={handleAdd} style={{ marginBottom: "1rem", alignItems: "flex-end" }}>
          {error && <div className="auth-error">{error}</div>}
          <label>
            Tracking Number
            <input value={trackingNumber} onChange={(e) => setTrackingNumber(e.target.value)} placeholder="1Z999AA10123456784" required />
          </label>
          <button type="submit" className="btn-primary">Add</button>
        </form>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead><tr><th>Carrier</th><th>Tracking #</th><th>Status</th><th>Last Checked</th><th></th></tr></thead>
          <tbody>
            {shipments.map((s) => (
              <tr key={s.id}>
                <td style={{ textTransform: "uppercase" }}>{s.carrier}</td>
                <td>
                  {s.tracking_url ? (
                    <a href={s.tracking_url} target="_blank" rel="noreferrer">{s.tracking_number}</a>
                  ) : s.tracking_number}
                </td>
                <td>
                  <select value={s.status} onChange={(e) => updateStatus(s, e.target.value)}>
                    {STATUSES.map((st) => <option key={st} value={st}>{st.replace(/_/g, " ")}</option>)}
                  </select>
                  {s.status_source === "manual" && <span className="text-muted" style={{ fontSize: "0.75rem", marginLeft: "0.4rem" }}>manual</span>}
                </td>
                <td>{s.last_checked_at ? new Date(s.last_checked_at).toLocaleString() : "Never"}</td>
                <td className="button-row">
                  <button type="button" className="btn-link" onClick={() => refresh(s)}>Refresh</button>
                  <button type="button" className="btn-link" onClick={() => remove(s)}>Remove</button>
                </td>
              </tr>
            ))}
            {shipments.length === 0 && <tr><td colSpan={5} className="empty-row">No tracking numbers yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

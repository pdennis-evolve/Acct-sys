import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

const REFERENCE_ROUTES = {
  purchase_order: (id) => `/purchase-orders/${id}`,
  invoice: (id) => `/invoices/${id}`,
  load: (id) => `/loads/${id}`,
};

const REFERENCE_LABELS = {
  purchase_order: "Purchase Order",
  invoice: "Invoice",
  load: "Load",
};

export default function TrackingList() {
  const [shipments, setShipments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get("/shipments").then((res) => setShipments(res.data.shipments)).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>Order Tracking</h1>
      <p className="text-muted">
        All tracking numbers attached to purchase orders, invoices, and loads across the company.
        Add or update tracking from the record itself.
      </p>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Attached To</th><th>Carrier</th><th>Tracking #</th><th>Status</th><th>Last Checked</th></tr>
          </thead>
          <tbody>
            {shipments.map((s) => (
              <tr key={s.id}>
                <td>
                  <Link to={REFERENCE_ROUTES[s.reference_type]?.(s.reference_id) || "#"}>
                    {REFERENCE_LABELS[s.reference_type] || s.reference_type}
                  </Link>
                </td>
                <td style={{ textTransform: "uppercase" }}>{s.carrier}</td>
                <td>
                  {s.tracking_url ? <a href={s.tracking_url} target="_blank" rel="noreferrer">{s.tracking_number}</a> : s.tracking_number}
                </td>
                <td><span className={`badge badge-${s.status}`}>{s.status.replace(/_/g, " ")}</span></td>
                <td>{s.last_checked_at ? new Date(s.last_checked_at).toLocaleString() : "Never"}</td>
              </tr>
            ))}
            {shipments.length === 0 && <tr><td colSpan={5} className="empty-row">No tracking numbers yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

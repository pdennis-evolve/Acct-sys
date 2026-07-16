import { useEffect, useState } from "react";
import portalClient from "../../api/portalClient";

export default function PortalTracking() {
  const [shipments, setShipments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    portalClient.get("/tracking").then((res) => setShipments(res.data.shipments)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading...</div>;

  return (
    <div>
      <h1>Shipment Tracking</h1>
      <table className="data-table">
        <thead>
          <tr><th>Carrier</th><th>Tracking #</th><th>Status</th><th>Last Checked</th></tr>
        </thead>
        <tbody>
          {shipments.map((s) => (
            <tr key={s.id}>
              <td style={{ textTransform: "uppercase" }}>{s.carrier}</td>
              <td>
                {s.tracking_url ? <a href={s.tracking_url} target="_blank" rel="noreferrer">{s.tracking_number}</a> : s.tracking_number}
              </td>
              <td><span className={`badge badge-${s.status}`}>{s.status.replace(/_/g, " ")}</span></td>
              <td>{s.last_checked_at ? new Date(s.last_checked_at).toLocaleString() : "Not yet checked"}</td>
            </tr>
          ))}
          {shipments.length === 0 && <tr><td colSpan={4} className="empty-row">No shipments to track yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

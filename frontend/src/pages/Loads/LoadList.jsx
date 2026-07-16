import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

const STATUSES = ["", "draft", "scheduled", "dispatched", "in_transit", "delivered", "invoiced", "cancelled"];

export default function LoadList() {
  const [loads, setLoads] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    client.get("/loads", { params: status ? { status } : {} }).then((res) => setLoads(res.data.loads)).finally(() => setLoading(false));
  }, [status]);

  return (
    <div>
      <div className="page-header">
        <h1>Loads</h1>
        <Link to="/loads/new" className="btn-primary">New Load</Link>
      </div>

      <div className="filter-bar">
        {STATUSES.map((s) => (
          <button key={s || "all"} className={`filter-chip ${status === s ? "active" : ""}`} onClick={() => setStatus(s)}>
            {s ? s.replace(/_/g, " ") : "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Load #</th><th>Customer</th><th>Route</th><th>Status</th><th>Driver</th><th>Vehicle</th><th>Total</th></tr>
          </thead>
          <tbody>
            {loads.map((l) => (
              <tr key={l.id}>
                <td><Link to={`/loads/${l.id}`}>{l.load_number}</Link></td>
                <td>{l.customer_name}</td>
                <td>{l.origin || "?"} &rarr; {l.destination || "?"}</td>
                <td><span className={`badge badge-${l.status}`}>{l.status.replace(/_/g, " ")}</span></td>
                <td>{l.driver_name || "-"}</td>
                <td>{l.vehicle_unit_number || "-"}</td>
                <td>${l.total}</td>
              </tr>
            ))}
            {loads.length === 0 && <tr><td colSpan={7} className="empty-row">No loads found.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";

const STATUSES = ["", "draft", "scheduled", "in_progress", "completed", "invoiced", "cancelled"];

export default function WorkOrderList() {
  const { hasRole } = useAuth();
  const [wos, setWos] = useState([]);
  const [status, setStatus] = useState("");
  const [mineOnly, setMineOnly] = useState(hasRole("technician"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (status) params.status = status;
    if (mineOnly) params.mine = "true";
    client.get("/work-orders", { params }).then((res) => setWos(res.data.work_orders)).finally(() => setLoading(false));
  }, [status, mineOnly]);

  return (
    <div>
      <div className="page-header">
        <h1>Work Orders</h1>
        {!hasRole("technician") && <Link to="/work-orders/new" className="btn-primary">New Work Order</Link>}
      </div>

      <div className="filter-bar">
        {STATUSES.map((s) => (
          <button key={s || "all"} className={`filter-chip ${status === s ? "active" : ""}`} onClick={() => setStatus(s)}>
            {s ? s.replace(/_/g, " ") : "All"}
          </button>
        ))}
      </div>
      {hasRole("technician") && (
        <div className="filter-bar">
          <button className={`filter-chip ${mineOnly ? "active" : ""}`} onClick={() => setMineOnly(true)}>My Jobs</button>
          <button className={`filter-chip ${!mineOnly ? "active" : ""}`} onClick={() => setMineOnly(false)}>All Jobs</button>
        </div>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>WO #</th><th>Customer</th><th>Status</th><th>Technician</th><th>Scheduled</th><th>Subtotal</th></tr>
          </thead>
          <tbody>
            {wos.map((w) => (
              <tr key={w.id}>
                <td><Link to={`/work-orders/${w.id}`}>{w.wo_number}</Link></td>
                <td>{w.customer_name}</td>
                <td><span className={`badge badge-${w.status}`}>{w.status.replace(/_/g, " ")}</span></td>
                <td>{w.technician_name || "Unassigned"}</td>
                <td>{w.scheduled_date || "-"}</td>
                <td>${w.subtotal}</td>
              </tr>
            ))}
            {wos.length === 0 && <tr><td colSpan={6} className="empty-row">No work orders found.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

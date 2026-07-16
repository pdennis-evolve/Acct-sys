import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import portalClient from "../../api/portalClient";

export default function PortalWorkOrderList() {
  const [workOrders, setWorkOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    portalClient.get("/work-orders").then((res) => setWorkOrders(res.data.work_orders)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading...</div>;

  return (
    <div>
      <h1>Your Work Orders</h1>
      <table className="data-table">
        <thead>
          <tr><th>Number</th><th>Status</th><th>Description</th><th>Scheduled</th></tr>
        </thead>
        <tbody>
          {workOrders.map((wo) => (
            <tr key={wo.id}>
              <td><Link to={`/portal/work-orders/${wo.id}`}>{wo.wo_number}</Link></td>
              <td><span className={`badge badge-${wo.status}`}>{wo.status.replace(/_/g, " ")}</span></td>
              <td>{wo.problem_description || "-"}</td>
              <td>{wo.scheduled_date || "-"}</td>
            </tr>
          ))}
          {workOrders.length === 0 && <tr><td colSpan={4} className="empty-row">No work orders yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

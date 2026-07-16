import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import portalClient from "../../api/portalClient";

export default function PortalWorkOrderDetail() {
  const { id } = useParams();
  const [workOrder, setWorkOrder] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    portalClient.get(`/work-orders/${id}`).then((res) => setWorkOrder(res.data.work_order)).finally(() => setLoading(false));
  }, [id]);

  if (loading || !workOrder) return <div className="page-loading">Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h1>{workOrder.wo_number}</h1>
      </div>

      <span className={`badge badge-${workOrder.status}`}>{workOrder.status.replace(/_/g, " ")}</span>

      <div className="card">
        <div className="form-row">
          <div><strong>Scheduled:</strong> {workOrder.scheduled_date || "-"}</div>
          <div><strong>Completed:</strong> {workOrder.completed_at ? new Date(workOrder.completed_at).toLocaleString() : "-"}</div>
        </div>
        <p>{workOrder.problem_description}</p>

        <table className="data-table" style={{ marginTop: "1rem" }}>
          <thead>
            <tr><th>Description</th><th>Qty</th></tr>
          </thead>
          <tbody>
            {(workOrder.lines || []).map((l, idx) => (
              <tr key={idx}>
                <td>{l.description}</td>
                <td>{l.quantity}</td>
              </tr>
            ))}
            {(!workOrder.lines || workOrder.lines.length === 0) && (
              <tr><td colSpan={2} className="empty-row">No line items.</td></tr>
            )}
          </tbody>
        </table>

        {workOrder.converted_invoice_id && (
          <p style={{ marginTop: "1rem" }}>
            <Link to={`/portal/invoices/${workOrder.converted_invoice_id}`}>View related invoice</Link>
          </p>
        )}
      </div>

      <Link to="/portal/work-orders" className="btn-link">Back to work orders</Link>
    </div>
  );
}

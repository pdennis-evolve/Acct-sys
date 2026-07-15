import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

const STATUSES = ["", "draft", "sent", "received", "closed", "cancelled"];

export default function POList() {
  const [pos, setPos] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    client
      .get("/purchase-orders", { params: status ? { status } : {} })
      .then((res) => setPos(res.data.purchase_orders))
      .finally(() => setLoading(false));
  }, [status]);

  return (
    <div>
      <div className="page-header">
        <h1>Purchase Orders</h1>
        <Link to="/purchase-orders/new" className="btn-primary">New Purchase Order</Link>
      </div>

      <div className="filter-bar">
        {STATUSES.map((s) => (
          <button
            key={s || "all"}
            className={`filter-chip ${status === s ? "active" : ""}`}
            onClick={() => setStatus(s)}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>PO #</th>
              <th>Vendor</th>
              <th>Status</th>
              <th>Order Date</th>
              <th>Expected Date</th>
              <th>Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {pos.map((p) => (
              <tr key={p.id}>
                <td><Link to={`/purchase-orders/${p.id}`}>{p.po_number}</Link></td>
                <td>{p.vendor_name}</td>
                <td><span className={`badge badge-${p.status}`}>{p.status}</span></td>
                <td>{p.order_date}</td>
                <td>{p.expected_date || "-"}</td>
                <td>${p.subtotal}</td>
              </tr>
            ))}
            {pos.length === 0 && <tr><td colSpan={6} className="empty-row">No purchase orders found.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

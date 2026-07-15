import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

const STATUSES = ["", "draft", "pending_approval", "approved", "partial", "paid", "void"];

export default function BillList() {
  const [bills, setBills] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    client
      .get("/bills", { params: status ? { status } : {} })
      .then((res) => setBills(res.data.bills))
      .finally(() => setLoading(false));
  }, [status]);

  return (
    <div>
      <div className="page-header">
        <h1>Bills</h1>
        <Link to="/bills/new" className="btn-primary">New Bill</Link>
      </div>

      <div className="filter-bar">
        {STATUSES.map((s) => (
          <button
            key={s || "all"}
            className={`filter-chip ${status === s ? "active" : ""}`}
            onClick={() => setStatus(s)}
          >
            {s ? s.replace(/_/g, " ") : "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Bill #</th>
              <th>Vendor</th>
              <th>Status</th>
              <th>Bill Date</th>
              <th>Due Date</th>
              <th>Total</th>
              <th>Balance Due</th>
            </tr>
          </thead>
          <tbody>
            {bills.map((b) => (
              <tr key={b.id}>
                <td><Link to={`/bills/${b.id}`}>{b.bill_number || b.id.slice(0, 8)}</Link></td>
                <td>{b.vendor_name}</td>
                <td><span className={`badge badge-${b.status}`}>{b.status.replace(/_/g, " ")}</span></td>
                <td>{b.bill_date}</td>
                <td>{b.due_date}</td>
                <td>${b.total}</td>
                <td>${b.balance_due}</td>
              </tr>
            ))}
            {bills.length === 0 && <tr><td colSpan={7} className="empty-row">No bills found.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

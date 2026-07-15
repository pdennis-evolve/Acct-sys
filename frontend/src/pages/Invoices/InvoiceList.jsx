import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

export default function InvoiceList() {
  const [invoices, setInvoices] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    client
      .get("/invoices", { params: status ? { status } : {} })
      .then((res) => setInvoices(res.data.invoices))
      .finally(() => setLoading(false));
  }, [status]);

  return (
    <div>
      <div className="page-header">
        <h1>Invoices</h1>
        <Link to="/invoices/new" className="btn-primary">New Invoice</Link>
      </div>

      <div className="filter-bar">
        {["", "draft", "sent", "partial", "paid", "void"].map((s) => (
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
              <th>Number</th>
              <th>Customer</th>
              <th>Status</th>
              <th>Issue Date</th>
              <th>Due Date</th>
              <th>Total</th>
              <th>Balance Due</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id}>
                <td><Link to={`/invoices/${inv.id}`}>{inv.invoice_number}</Link></td>
                <td>{inv.customer_name}</td>
                <td><span className={`badge badge-${inv.status}`}>{inv.status}</span></td>
                <td>{inv.issue_date}</td>
                <td>{inv.due_date}</td>
                <td>${inv.total}</td>
                <td>${inv.balance_due}</td>
              </tr>
            ))}
            {invoices.length === 0 && <tr><td colSpan={7} className="empty-row">No invoices found.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

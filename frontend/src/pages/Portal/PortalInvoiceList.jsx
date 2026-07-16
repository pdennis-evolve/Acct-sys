import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import portalClient from "../../api/portalClient";

export default function PortalInvoiceList() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    portalClient.get("/invoices").then((res) => setInvoices(res.data.invoices)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading...</div>;

  return (
    <div>
      <h1>Your Invoices</h1>
      <table className="data-table">
        <thead>
          <tr><th>Number</th><th>Status</th><th>Issue Date</th><th>Due Date</th><th>Total</th><th>Balance Due</th></tr>
        </thead>
        <tbody>
          {invoices.map((inv) => (
            <tr key={inv.id}>
              <td><Link to={`/portal/invoices/${inv.id}`}>{inv.invoice_number}</Link></td>
              <td><span className={`badge badge-${inv.status}`}>{inv.status}</span></td>
              <td>{inv.issue_date}</td>
              <td>{inv.due_date}</td>
              <td>${inv.total}</td>
              <td>${inv.balance_due}</td>
            </tr>
          ))}
          {invoices.length === 0 && <tr><td colSpan={6} className="empty-row">No invoices yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

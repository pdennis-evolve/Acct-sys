import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

export default function PaymentList() {
  const [payments, setPayments] = useState([]);
  const [customers, setCustomers] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([client.get("/payments"), client.get("/customers")]).then(([payRes, custRes]) => {
      setPayments(payRes.data.payments);
      const map = {};
      custRes.data.customers.forEach((c) => (map[c.id] = c.display_name));
      setCustomers(map);
      setLoading(false);
    });
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Customer Receipts</h1>
        <Link to="/payments/new" className="btn-primary">Record Payment</Link>
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Date</th><th>Customer</th><th>Method</th><th>Reference</th><th>Amount</th><th>Unapplied</th></tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td>{p.payment_date}</td>
                <td>{customers[p.customer_id] || p.customer_id}</td>
                <td>{p.method}</td>
                <td>{p.reference_number || "-"}</td>
                <td>${p.amount}</td>
                <td>${p.amount_unapplied}</td>
              </tr>
            ))}
            {payments.length === 0 && <tr><td colSpan={6} className="empty-row">No payments recorded yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

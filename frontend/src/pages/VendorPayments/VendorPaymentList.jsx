import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

export default function VendorPaymentList() {
  const [payments, setPayments] = useState([]);
  const [vendors, setVendors] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([client.get("/vendor-payments"), client.get("/vendors")]).then(([payRes, vendRes]) => {
      setPayments(payRes.data.vendor_payments);
      const map = {};
      vendRes.data.vendors.forEach((v) => (map[v.id] = v.display_name));
      setVendors(map);
      setLoading(false);
    });
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Bill Payments</h1>
        <Link to="/vendor-payments/new" className="btn-primary">Pay a Bill</Link>
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Date</th><th>Vendor</th><th>Method</th><th>Reference</th><th>Amount</th><th>Unapplied</th></tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td>{p.payment_date}</td>
                <td>{vendors[p.vendor_id] || p.vendor_id}</td>
                <td>{p.method}</td>
                <td>{p.reference_number || "-"}</td>
                <td>${p.amount}</td>
                <td>${p.amount_unapplied}</td>
              </tr>
            ))}
            {payments.length === 0 && <tr><td colSpan={6} className="empty-row">No bill payments recorded yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

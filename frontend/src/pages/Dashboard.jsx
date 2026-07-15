import { useEffect, useState } from "react";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { user, tenant, hasModule } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hasModule("ar_ap")) {
      setLoading(false);
      return;
    }
    Promise.all([client.get("/invoices"), client.get("/customers")])
      .then(([invoicesRes, customersRes]) => {
        const invoices = invoicesRes.data.invoices;
        const outstanding = invoices
          .filter((i) => i.status !== "void")
          .reduce((sum, i) => sum + parseFloat(i.balance_due), 0);
        const overdue = invoices.filter(
          (i) => i.status === "sent" || i.status === "partial"
        ).filter((i) => new Date(i.due_date) < new Date()).length;

        setStats({
          customerCount: customersRes.data.customers.length,
          invoiceCount: invoices.length,
          outstanding,
          overdueCount: overdue,
        });
      })
      .finally(() => setLoading(false));
  }, [hasModule]);

  return (
    <div>
      <h1>Welcome, {user?.full_name}</h1>
      <p className="text-muted">{tenant?.name}</p>

      {!hasModule("ar_ap") && (
        <div className="card">AR/AP module is not enabled for this tenant.</div>
      )}

      {hasModule("ar_ap") && loading && <div className="page-loading">Loading...</div>}

      {hasModule("ar_ap") && stats && (
        <div className="stat-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.customerCount}</div>
            <div className="stat-label">Customers</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.invoiceCount}</div>
            <div className="stat-label">Invoices</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">${stats.outstanding.toFixed(2)}</div>
            <div className="stat-label">Outstanding Balance</div>
          </div>
          <div className="stat-card stat-warning">
            <div className="stat-value">{stats.overdueCount}</div>
            <div className="stat-label">Overdue Invoices</div>
          </div>
        </div>
      )}
    </div>
  );
}

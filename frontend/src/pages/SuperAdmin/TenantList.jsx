import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

export default function TenantList() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get("/admin/tenants").then((res) => setTenants(res.data.tenants)).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Tenants</h1>
        <Link to="/admin/tenants/new" className="btn-primary">New Tenant</Link>
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead><tr><th>Name</th><th>Slug</th><th>License</th><th>Seats</th><th>Status</th></tr></thead>
          <tbody>
            {tenants.map((t) => (
              <tr key={t.id}>
                <td><Link to={`/admin/tenants/${t.id}`}>{t.name}</Link></td>
                <td>{t.slug}</td>
                <td>{t.license_status}</td>
                <td>{t.seats_used} / {t.seat_limit}</td>
                <td><span className={`badge ${t.is_active ? "badge-active" : "badge-inactive"}`}>{t.is_active ? "Active" : "Disabled"}</span></td>
              </tr>
            ))}
            {tenants.length === 0 && <tr><td colSpan={5} className="empty-row">No tenants provisioned yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

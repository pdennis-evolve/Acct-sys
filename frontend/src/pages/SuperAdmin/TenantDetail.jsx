import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import client from "../../api/client";

const MODULES = [
  { key: "ar_ap", label: "AR/AP" },
  { key: "inventory", label: "Inventory" },
  { key: "work_orders", label: "Work Orders" },
  { key: "transportation", label: "Transportation" },
  { key: "order_tracking", label: "Order Tracking" },
  { key: "contract_manager", label: "Contract Manager" },
  { key: "customer_portal", label: "Customer Portal" },
  { key: "project_manager", label: "Project Manager" },
];

const LICENSE_STATUSES = ["trial", "active", "grace_period", "locked", "canceled"];

export default function TenantDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "", slug: "",
    modules: Object.fromEntries(MODULES.map((m) => [m.key, m.key === "ar_ap"])),
    seat_limit: 5,
    license_status: "trial",
    license_start: "",
    license_end: "",
    plan_notes: "",
    admin_email: "",
    admin_password: "",
    admin_name: "",
  });
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isNew) return;
    client.get(`/admin/tenants/${id}`).then((res) => {
      const t = res.data.tenant;
      setForm((f) => ({
        ...f,
        name: t.name,
        slug: t.slug,
        modules: t.modules,
        seat_limit: t.seat_limit,
        license_status: t.license_status,
        license_start: t.license_start || "",
        license_end: t.license_end || "",
      }));
      setLoading(false);
    });
  }, [id, isNew]);

  function toggleModule(key) {
    setForm((f) => ({ ...f, modules: { ...f.modules, [key]: !f.modules[key] } }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (isNew) {
        const res = await client.post("/admin/tenants", form);
        navigate(`/admin/tenants/${res.data.tenant.id}`);
      } else {
        const res = await client.patch(`/admin/tenants/${id}`, form);
        setForm((f) => ({ ...f, ...res.data.tenant }));
        setSaved(true);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="page-loading">Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New Tenant" : form.name}</h1>
        <Link to="/admin" className="btn-link">Back to tenants</Link>
      </div>

      {error && <div className="auth-error">{error}</div>}
      {saved && <div className="auth-success">Tenant updated.</div>}

      <form className="card form-grid" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            Tenant Name *
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Slug *
            <input value={form.slug} disabled={!isNew} onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase() })} required />
          </label>
        </div>

        <h3 className="form-section-title">Modules</h3>
        <div className="module-toggle-grid">
          {MODULES.map((m) => (
            <label key={m.key} className="module-toggle">
              <input type="checkbox" checked={!!form.modules[m.key]} onChange={() => toggleModule(m.key)} />
              {m.label}
            </label>
          ))}
        </div>

        <h3 className="form-section-title">License</h3>
        <div className="form-row">
          <label>
            Seat Limit
            <input type="number" value={form.seat_limit} onChange={(e) => setForm({ ...form, seat_limit: parseInt(e.target.value) || 0 })} />
          </label>
          <label>
            License Status
            <select value={form.license_status} onChange={(e) => setForm({ ...form, license_status: e.target.value })}>
              {LICENSE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
        </div>
        <div className="form-row">
          <label>
            License Start
            <input type="date" value={form.license_start} onChange={(e) => setForm({ ...form, license_start: e.target.value })} />
          </label>
          <label>
            License End
            <input type="date" value={form.license_end} onChange={(e) => setForm({ ...form, license_end: e.target.value })} />
          </label>
        </div>
        <label>
          Plan Notes (reference only — not used for pricing enforcement)
          <textarea value={form.plan_notes} onChange={(e) => setForm({ ...form, plan_notes: e.target.value })} rows={2} />
        </label>

        {isNew && (
          <>
            <h3 className="form-section-title">Initial Owner/Admin User</h3>
            <div className="form-row">
              <label>
                Name
                <input value={form.admin_name} onChange={(e) => setForm({ ...form, admin_name: e.target.value })} />
              </label>
              <label>
                Email
                <input type="email" value={form.admin_email} onChange={(e) => setForm({ ...form, admin_email: e.target.value })} />
              </label>
              <label>
                Password
                <input type="password" value={form.admin_password} onChange={(e) => setForm({ ...form, admin_password: e.target.value })} />
              </label>
            </div>
          </>
        )}

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving..." : isNew ? "Create Tenant" : "Save Changes"}
        </button>
      </form>
    </div>
  );
}

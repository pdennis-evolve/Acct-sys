import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";

const BLANK = {
  display_name: "",
  company_name: "",
  email: "",
  phone: "",
  notes: "",
  billing_address: { line1: "", line2: "", city: "", state: "", postal_code: "", country: "" },
};

export default function CustomerDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const { hasModule } = useAuth();

  const [form, setForm] = useState(BLANK);
  const [invoices, setInvoices] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [portalUsers, setPortalUsers] = useState([]);
  const [showNewPortalUser, setShowNewPortalUser] = useState(false);
  const [newPortalUser, setNewPortalUser] = useState({ email: "", full_name: "", password: "" });
  const [portalError, setPortalError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isNew) {
      setForm(BLANK);
      setInvoices([]);
      setContracts([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    client.get(`/customers/${id}`).then((res) => {
      const c = res.data.customer;
      setForm({
        display_name: c.display_name,
        company_name: c.company_name || "",
        email: c.email || "",
        phone: c.phone || "",
        notes: c.notes || "",
        billing_address: c.billing_address || BLANK.billing_address,
      });
      setLoading(false);
    });
    client.get("/invoices", { params: { customer_id: id } }).then((res) => setInvoices(res.data.invoices));
    if (hasModule("contract_manager")) {
      client.get("/contracts", { params: { customer_id: id } }).then((res) => setContracts(res.data.contracts));
    }
    if (hasModule("customer_portal")) {
      loadPortalUsers();
    }
  }, [id, isNew]);

  function loadPortalUsers() {
    client.get(`/customers/${id}/portal-users`).then((res) => setPortalUsers(res.data.portal_users));
  }

  async function handleCreatePortalUser(e) {
    e.preventDefault();
    setPortalError("");
    try {
      await client.post(`/customers/${id}/portal-users`, newPortalUser);
      setNewPortalUser({ email: "", full_name: "", password: "" });
      setShowNewPortalUser(false);
      loadPortalUsers();
    } catch (err) {
      setPortalError(err.response?.data?.error || "Could not create portal login");
    }
  }

  async function togglePortalUserActive(pu) {
    await client.patch(`/customers/${id}/portal-users/${pu.id}`, { is_active: !pu.is_active });
    loadPortalUsers();
  }

  function updateField(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }
  function updateAddress(field, value) {
    setForm((f) => ({ ...f, billing_address: { ...f.billing_address, [field]: value } }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (isNew) {
        const res = await client.post("/customers", form);
        navigate(`/customers/${res.data.customer.id}`);
      } else {
        await client.patch(`/customers/${id}`, form);
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
        <h1>{isNew ? "New Customer" : form.display_name}</h1>
        <Link to="/customers" className="btn-link">Back to customers</Link>
      </div>

      {error && <div className="auth-error">{error}</div>}

      <form className="card form-grid" onSubmit={handleSubmit}>
        <label>
          Display Name *
          <input value={form.display_name} onChange={(e) => updateField("display_name", e.target.value)} required />
        </label>
        <label>
          Company Name
          <input value={form.company_name} onChange={(e) => updateField("company_name", e.target.value)} />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={(e) => updateField("email", e.target.value)} />
        </label>
        <label>
          Phone
          <input value={form.phone} onChange={(e) => updateField("phone", e.target.value)} />
        </label>

        <h3 className="form-section-title">Billing Address</h3>
        <label>
          Address Line 1
          <input value={form.billing_address.line1 || ""} onChange={(e) => updateAddress("line1", e.target.value)} />
        </label>
        <label>
          Address Line 2
          <input value={form.billing_address.line2 || ""} onChange={(e) => updateAddress("line2", e.target.value)} />
        </label>
        <div className="form-row">
          <label>
            City
            <input value={form.billing_address.city || ""} onChange={(e) => updateAddress("city", e.target.value)} />
          </label>
          <label>
            State
            <input value={form.billing_address.state || ""} onChange={(e) => updateAddress("state", e.target.value)} />
          </label>
          <label>
            Postal Code
            <input value={form.billing_address.postal_code || ""} onChange={(e) => updateAddress("postal_code", e.target.value)} />
          </label>
        </div>

        <label>
          Notes
          <textarea value={form.notes} onChange={(e) => updateField("notes", e.target.value)} rows={3} />
        </label>

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving..." : isNew ? "Create Customer" : "Save Changes"}
        </button>
      </form>

      {!isNew && (
        <div className="card">
          <div className="page-header">
            <h2>Invoices</h2>
            <Link to={`/invoices/new?customer_id=${id}`} className="btn-secondary">New Invoice</Link>
          </div>
          <table className="data-table">
            <thead>
              <tr><th>Number</th><th>Status</th><th>Issue Date</th><th>Total</th><th>Balance Due</th></tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td><Link to={`/invoices/${inv.id}`}>{inv.invoice_number}</Link></td>
                  <td><span className={`badge badge-${inv.status}`}>{inv.status}</span></td>
                  <td>{inv.issue_date}</td>
                  <td>${inv.total}</td>
                  <td>${inv.balance_due}</td>
                </tr>
              ))}
              {invoices.length === 0 && <tr><td colSpan={5} className="empty-row">No invoices yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {!isNew && hasModule("contract_manager") && (
        <div className="card">
          <div className="page-header">
            <h2>Contracts</h2>
            <Link to={`/contracts/new?customer_id=${id}`} className="btn-secondary">New Contract</Link>
          </div>
          <table className="data-table">
            <thead>
              <tr><th>Title</th><th>Status</th><th>Start</th><th>End</th><th>Renewal</th></tr>
            </thead>
            <tbody>
              {contracts.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/contracts/${c.id}`}>{c.title}</Link></td>
                  <td>
                    <span className={`badge badge-${c.status}`}>{c.status}</span>
                    {c.is_expiring_soon && <span className="badge badge-sent" style={{ marginLeft: "0.3rem" }}>Expiring Soon</span>}
                  </td>
                  <td>{c.start_date || "-"}</td>
                  <td>{c.end_date || "-"}</td>
                  <td>{c.renewal_date || "-"}</td>
                </tr>
              ))}
              {contracts.length === 0 && <tr><td colSpan={5} className="empty-row">No contracts yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {!isNew && hasModule("customer_portal") && (
        <div className="card">
          <div className="page-header">
            <h2>Portal Access</h2>
            <button type="button" className="btn-secondary" onClick={() => setShowNewPortalUser((s) => !s)}>
              {showNewPortalUser ? "Cancel" : "New Portal Login"}
            </button>
          </div>

          {portalError && <div className="auth-error">{portalError}</div>}

          {showNewPortalUser && (
            <form className="form-grid" onSubmit={handleCreatePortalUser} style={{ marginBottom: "1rem" }}>
              <label>
                Full Name
                <input
                  value={newPortalUser.full_name}
                  onChange={(e) => setNewPortalUser((f) => ({ ...f, full_name: e.target.value }))}
                  required
                />
              </label>
              <label>
                Email
                <input
                  type="email"
                  value={newPortalUser.email}
                  onChange={(e) => setNewPortalUser((f) => ({ ...f, email: e.target.value }))}
                  required
                />
              </label>
              <label>
                Initial Password
                <input
                  type="password"
                  value={newPortalUser.password}
                  onChange={(e) => setNewPortalUser((f) => ({ ...f, password: e.target.value }))}
                  minLength={8}
                  required
                />
              </label>
              <button type="submit" className="btn-primary">Create Login</button>
            </form>
          )}

          <table className="data-table">
            <thead>
              <tr><th>Name</th><th>Email</th><th>Status</th><th>Last Login</th><th></th></tr>
            </thead>
            <tbody>
              {portalUsers.map((pu) => (
                <tr key={pu.id}>
                  <td>{pu.full_name}</td>
                  <td>{pu.email}</td>
                  <td><span className={`badge ${pu.is_active ? "badge-paid" : "badge-void"}`}>{pu.is_active ? "Active" : "Deactivated"}</span></td>
                  <td>{pu.last_login_at ? new Date(pu.last_login_at).toLocaleString() : "Never"}</td>
                  <td>
                    <button type="button" className="btn-link" onClick={() => togglePortalUserActive(pu)}>
                      {pu.is_active ? "Deactivate" : "Reactivate"}
                    </button>
                  </td>
                </tr>
              ))}
              {portalUsers.length === 0 && <tr><td colSpan={5} className="empty-row">No portal logins yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

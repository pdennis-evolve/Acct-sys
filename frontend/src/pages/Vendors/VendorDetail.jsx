import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import client from "../../api/client";

const BLANK = {
  display_name: "",
  company_name: "",
  email: "",
  phone: "",
  notes: "",
  address: { line1: "", line2: "", city: "", state: "", postal_code: "", country: "" },
};

export default function VendorDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();

  const [form, setForm] = useState(BLANK);
  const [bills, setBills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isNew) {
      setForm(BLANK);
      setBills([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    client.get(`/vendors/${id}`).then((res) => {
      const v = res.data.vendor;
      setForm({
        display_name: v.display_name,
        company_name: v.company_name || "",
        email: v.email || "",
        phone: v.phone || "",
        notes: v.notes || "",
        address: v.address || BLANK.address,
      });
      setLoading(false);
    });
    client.get("/bills", { params: { vendor_id: id } }).then((res) => setBills(res.data.bills));
  }, [id, isNew]);

  function updateField(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }
  function updateAddress(field, value) {
    setForm((f) => ({ ...f, address: { ...f.address, [field]: value } }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (isNew) {
        const res = await client.post("/vendors", form);
        navigate(`/vendors/${res.data.vendor.id}`);
      } else {
        await client.patch(`/vendors/${id}`, form);
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
        <h1>{isNew ? "New Vendor" : form.display_name}</h1>
        <Link to="/vendors" className="btn-link">Back to vendors</Link>
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

        <h3 className="form-section-title">Address</h3>
        <label>
          Address Line 1
          <input value={form.address.line1 || ""} onChange={(e) => updateAddress("line1", e.target.value)} />
        </label>
        <label>
          Address Line 2
          <input value={form.address.line2 || ""} onChange={(e) => updateAddress("line2", e.target.value)} />
        </label>
        <div className="form-row">
          <label>
            City
            <input value={form.address.city || ""} onChange={(e) => updateAddress("city", e.target.value)} />
          </label>
          <label>
            State
            <input value={form.address.state || ""} onChange={(e) => updateAddress("state", e.target.value)} />
          </label>
          <label>
            Postal Code
            <input value={form.address.postal_code || ""} onChange={(e) => updateAddress("postal_code", e.target.value)} />
          </label>
        </div>

        <label>
          Notes
          <textarea value={form.notes} onChange={(e) => updateField("notes", e.target.value)} rows={3} />
        </label>

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving..." : isNew ? "Create Vendor" : "Save Changes"}
        </button>
      </form>

      {!isNew && (
        <div className="card">
          <div className="page-header">
            <h2>Bills</h2>
            <Link to={`/bills/new?vendor_id=${id}`} className="btn-secondary">New Bill</Link>
          </div>
          <table className="data-table">
            <thead>
              <tr><th>Bill #</th><th>Status</th><th>Bill Date</th><th>Total</th><th>Balance Due</th></tr>
            </thead>
            <tbody>
              {bills.map((b) => (
                <tr key={b.id}>
                  <td><Link to={`/bills/${b.id}`}>{b.bill_number || b.id.slice(0, 8)}</Link></td>
                  <td><span className={`badge badge-${b.status}`}>{b.status.replace(/_/g, " ")}</span></td>
                  <td>{b.bill_date}</td>
                  <td>${b.total}</td>
                  <td>${b.balance_due}</td>
                </tr>
              ))}
              {bills.length === 0 && <tr><td colSpan={5} className="empty-row">No bills yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

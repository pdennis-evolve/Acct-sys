import { useEffect, useState } from "react";
import client from "../../api/client";

export default function CompanySettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    client.get("/settings").then((res) => setForm(res.data.settings));
  }, []);

  function updateField(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    setSaved(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const res = await client.patch("/settings", form);
      setForm(res.data.settings);
      setSaved(true);
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (!form) return <div className="page-loading">Loading...</div>;

  return (
    <div>
      <h1>Company Settings</h1>
      {error && <div className="auth-error">{error}</div>}
      {saved && <div className="auth-success">Settings saved.</div>}

      <form className="card form-grid" onSubmit={handleSubmit}>
        <label>
          Company Name *
          <input value={form.company_name} onChange={(e) => updateField("company_name", e.target.value)} required />
        </label>
        <label>
          Address Line 1
          <input value={form.address_line1 || ""} onChange={(e) => updateField("address_line1", e.target.value)} />
        </label>
        <label>
          Address Line 2
          <input value={form.address_line2 || ""} onChange={(e) => updateField("address_line2", e.target.value)} />
        </label>
        <div className="form-row">
          <label>
            City
            <input value={form.city || ""} onChange={(e) => updateField("city", e.target.value)} />
          </label>
          <label>
            State
            <input value={form.state || ""} onChange={(e) => updateField("state", e.target.value)} />
          </label>
          <label>
            Postal Code
            <input value={form.postal_code || ""} onChange={(e) => updateField("postal_code", e.target.value)} />
          </label>
        </div>
        <div className="form-row">
          <label>
            Phone
            <input value={form.phone || ""} onChange={(e) => updateField("phone", e.target.value)} />
          </label>
          <label>
            Email
            <input type="email" value={form.email || ""} onChange={(e) => updateField("email", e.target.value)} />
          </label>
        </div>

        <h3 className="form-section-title">Invoicing</h3>
        <div className="form-row">
          <label>
            Invoice Prefix
            <input value={form.invoice_prefix} onChange={(e) => updateField("invoice_prefix", e.target.value)} />
          </label>
          <label>
            Next Invoice Number
            <input type="number" value={form.next_invoice_number} onChange={(e) => updateField("next_invoice_number", parseInt(e.target.value) || 0)} />
          </label>
          <label>
            Default Terms (days)
            <input type="number" value={form.default_invoice_terms_days} onChange={(e) => updateField("default_invoice_terms_days", parseInt(e.target.value) || 0)} />
          </label>
        </div>

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving..." : "Save Settings"}
        </button>
      </form>
    </div>
  );
}

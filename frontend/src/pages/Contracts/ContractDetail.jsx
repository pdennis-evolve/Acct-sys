import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
import client from "../../api/client";

export default function ContractDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [contract, setContract] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [customerId, setCustomerId] = useState(searchParams.get("customer_id") || "");
  const [title, setTitle] = useState("");
  const [contractNumber, setContractNumber] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [renewalDate, setRenewalDate] = useState("");
  const [autoRenew, setAutoRenew] = useState(false);
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  function loadDetail() {
    if (isNew) {
      setContract(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    client.get(`/contracts/${id}`).then((res) => {
      const c = res.data.contract;
      setContract(c);
      setTitle(c.title);
      setContractNumber(c.contract_number || "");
      setStartDate(c.start_date || "");
      setEndDate(c.end_date || "");
      setRenewalDate(c.renewal_date || "");
      setAutoRenew(c.auto_renew);
      setNotes(c.notes || "");
      setLoading(false);
    });
  }

  useEffect(() => {
    if (isNew) client.get("/customers").then((res) => setCustomers(res.data.customers));
    loadDetail();
  }, [id, isNew]);

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    if (!customerId) {
      setError("Please select a customer");
      return;
    }
    if (!title.trim()) {
      setError("Please enter a title");
      return;
    }
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("customer_id", customerId);
      formData.append("title", title);
      if (contractNumber) formData.append("contract_number", contractNumber);
      if (startDate) formData.append("start_date", startDate);
      if (endDate) formData.append("end_date", endDate);
      if (renewalDate) formData.append("renewal_date", renewalDate);
      formData.append("auto_renew", autoRenew ? "true" : "false");
      if (notes) formData.append("notes", notes);
      if (file) formData.append("file", file);

      const res = await client.post("/contracts", formData);
      navigate(`/contracts/${res.data.contract.id}`);
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveMeta(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const res = await client.patch(`/contracts/${id}`, {
        title, contract_number: contractNumber,
        start_date: startDate || null, end_date: endDate || null, renewal_date: renewalDate || null,
        auto_renew: autoRenew, notes,
      });
      setContract(res.data.contract);
      setInfo("Saved.");
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function setStatus(status) {
    const res = await client.patch(`/contracts/${id}`, { status });
    setContract(res.data.contract);
  }

  async function handleDownload() {
    const res = await client.get(`/contracts/${id}/file`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = contract.file_name || "contract";
    a.click();
    window.URL.revokeObjectURL(url);
  }

  async function handleDelete() {
    if (!confirm("Delete this contract record?")) return;
    await client.delete(`/contracts/${id}`);
    navigate("/contracts");
  }

  if (loading || (!isNew && !contract)) return <div className="page-loading">Loading...</div>;

  if (isNew) {
    return (
      <div>
        <div className="page-header">
          <h1>New Contract</h1>
          <Link to="/contracts" className="btn-link">Back to contracts</Link>
        </div>
        {error && <div className="auth-error">{error}</div>}
        <form className="card form-grid" onSubmit={handleCreate}>
          <label>
            Customer *
            <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
              <option value="">Select a customer...</option>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.display_name}</option>)}
            </select>
          </label>
          <div className="form-row">
            <label>
              Title *
              <input value={title} onChange={(e) => setTitle(e.target.value)} required />
            </label>
            <label>
              Contract Number
              <input value={contractNumber} onChange={(e) => setContractNumber(e.target.value)} />
            </label>
          </div>

          <label>
            Contract File (PDF or DOCX)
            <input type="file" accept=".pdf,.docx" onChange={(e) => setFile(e.target.files[0])} />
          </label>
          <p className="text-muted">
            If a file is attached, we'll scan it for Effective/Expiration/Renewal dates and pre-fill
            any date fields below that you leave blank. Always double-check extracted dates.
          </p>

          <div className="form-row">
            <label>
              Start Date
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </label>
            <label>
              End Date
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </label>
            <label>
              Renewal Date
              <input type="date" value={renewalDate} onChange={(e) => setRenewalDate(e.target.value)} />
            </label>
          </div>

          <label className="module-toggle">
            <input type="checkbox" checked={autoRenew} onChange={(e) => setAutoRenew(e.target.checked)} />
            Auto-renews
          </label>

          <label>
            Notes
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
          </label>

          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Uploading..." : "Create Contract"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>{contract.title}</h1>
        <div className="button-row">
          {contract.has_file && <button className="btn-secondary" onClick={handleDownload}>Download File</button>}
          {contract.status === "draft" && <button className="btn-primary" onClick={() => setStatus("active")}>Activate</button>}
          {contract.status === "active" && <button className="btn-secondary" onClick={() => setStatus("renewed")}>Mark Renewed</button>}
          {contract.status === "active" && <button className="btn-danger" onClick={() => setStatus("terminated")}>Terminate</button>}
          <button className="btn-danger" onClick={handleDelete}>Delete</button>
        </div>
      </div>

      <div className="button-row" style={{ marginBottom: "1rem" }}>
        <span className={`badge badge-${contract.status}`}>{contract.status}</span>
        {contract.is_expired && <span className="badge badge-cancelled">Expired</span>}
        {contract.is_expiring_soon && <span className="badge badge-sent">Expiring Soon</span>}
        {contract.dates_auto_extracted && <span className="badge badge-pending">Dates auto-extracted &mdash; please review</span>}
      </div>

      {error && <div className="auth-error">{error}</div>}
      {info && <div className="auth-success">{info}</div>}

      <p className="text-muted"><strong>Customer:</strong> {contract.customer_name}</p>
      {contract.file_name && <p className="text-muted"><strong>File:</strong> {contract.file_name}</p>}

      <form className="card form-grid" onSubmit={handleSaveMeta}>
        <div className="form-row">
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            Contract Number
            <input value={contractNumber} onChange={(e) => setContractNumber(e.target.value)} />
          </label>
        </div>

        <div className="form-row">
          <label>
            Start Date
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>
            End Date
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
          <label>
            Renewal Date
            <input type="date" value={renewalDate} onChange={(e) => setRenewalDate(e.target.value)} />
          </label>
        </div>

        <label className="module-toggle">
          <input type="checkbox" checked={autoRenew} onChange={(e) => setAutoRenew(e.target.checked)} />
          Auto-renews
        </label>

        <label>
          Notes
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
        </label>

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </form>
    </div>
  );
}

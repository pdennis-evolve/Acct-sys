import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";

const BLANK_LINE = () => ({ line_type: "labor", description: "", quantity: 1, unit_price: 0, item_id: "", account_id: "" });

export default function WorkOrderDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { hasRole, hasModule, user } = useAuth();

  const [wo, setWo] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [items, setItems] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [customerId, setCustomerId] = useState(searchParams.get("customer_id") || "");
  const [assignedTo, setAssignedTo] = useState("");
  const [scheduledDate, setScheduledDate] = useState("");
  const [problemDescription, setProblemDescription] = useState("");
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState([BLANK_LINE()]);
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const isDispatchRole = hasRole("owner_admin", "accountant", "dispatcher");
  const inventoryEnabled = hasModule("inventory");
  const projectManagerEnabled = hasModule("project_manager");

  useEffect(() => {
    if (isDispatchRole) {
      client.get("/customers").then((res) => setCustomers(res.data.customers));
      client.get("/work-orders/technicians").then((res) => setTechnicians(res.data.technicians));
    }
    if (projectManagerEnabled) {
      client.get("/projects").then((res) => setProjects(res.data.projects));
    }
    client.get("/accounts").then((res) => setAccounts(res.data.accounts.filter((a) => a.type === "income")));
    if (inventoryEnabled) {
      client.get("/items").then((res) => setItems(res.data.items.filter((i) => i.is_active)));
    }

    if (isNew) {
      setWo(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    client.get(`/work-orders/${id}`).then((res) => {
      const w = res.data.work_order;
      setWo(w);
      setAssignedTo(w.assigned_to || "");
      setScheduledDate(w.scheduled_date || "");
      setProblemDescription(w.problem_description || "");
      setMemo(w.memo || "");
      setProjectId(w.project_id || "");
      setLines(w.lines.length ? w.lines : [BLANK_LINE()]);
      setLoading(false);
    });
  }, [id, isNew]);

  function updateLine(idx, field, value) {
    setLines((ls) => ls.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));
  }
  function applyItem(idx, itemId) {
    const item = items.find((i) => i.id === itemId);
    setLines((ls) => ls.map((l, i) => {
      if (i !== idx) return l;
      if (!item) return { ...l, item_id: "" };
      return { ...l, item_id: item.id, description: l.description || item.name, unit_price: item.unit_price };
    }));
  }
  function addLine(lineType) {
    setLines((ls) => [...ls, { ...BLANK_LINE(), line_type: lineType }]);
  }
  function removeLine(idx) {
    setLines((ls) => ls.filter((_, i) => i !== idx));
  }

  const subtotal = lines.reduce((sum, l) => sum + (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0), 0);

  async function handleSave(e) {
    e.preventDefault();
    setError("");
    if (isNew && !customerId) {
      setError("Please select a customer");
      return;
    }
    setSaving(true);
    try {
      const payload = { lines, memo, problem_description: problemDescription };
      if (projectManagerEnabled) payload.project_id = projectId || null;
      if (isNew) {
        payload.customer_id = customerId;
        if (assignedTo) payload.assigned_to = assignedTo;
        if (scheduledDate) payload.scheduled_date = scheduledDate;
        const res = await client.post("/work-orders", payload);
        navigate(`/work-orders/${res.data.work_order.id}`);
      } else {
        const res = await client.patch(`/work-orders/${id}`, payload);
        setWo(res.data.work_order);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSchedule() {
    setError("");
    if (!scheduledDate) {
      setError("Pick a scheduled date first");
      return;
    }
    try {
      const res = await client.post(`/work-orders/${id}/schedule`, { scheduled_date: scheduledDate, assigned_to: assignedTo || null });
      setWo(res.data.work_order);
    } catch (err) {
      setError(err.response?.data?.error || "Schedule failed");
    }
  }
  async function handleStart() {
    const res = await client.post(`/work-orders/${id}/start`);
    setWo(res.data.work_order);
  }
  async function handleComplete() {
    setError("");
    try {
      const res = await client.post(`/work-orders/${id}/complete`);
      setWo(res.data.work_order);
    } catch (err) {
      setError(err.response?.data?.error || "Complete failed");
    }
  }
  async function handleCancel() {
    if (!confirm("Cancel this work order?")) return;
    const res = await client.post(`/work-orders/${id}/cancel`);
    setWo(res.data.work_order);
  }
  async function handleConvertToInvoice() {
    const res = await client.post(`/work-orders/${id}/convert-to-invoice`);
    navigate(`/invoices/${res.data.invoice.id}`);
  }

  if (loading || (!isNew && !wo)) return <div className="page-loading">Loading...</div>;

  const canManage = isDispatchRole || (hasRole("technician") && wo?.assigned_to === user?.id);
  const editable = isNew || (canManage && wo && ["draft", "scheduled", "in_progress"].includes(wo.status));

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New Work Order" : wo.wo_number}</h1>
        <div className="button-row">
          {!isNew && wo.status === "draft" && isDispatchRole && (
            <button className="btn-secondary" onClick={handleSchedule}>Schedule</button>
          )}
          {!isNew && wo.status === "scheduled" && canManage && (
            <button className="btn-secondary" onClick={handleStart}>Start Work</button>
          )}
          {!isNew && wo.status === "in_progress" && canManage && (
            <button className="btn-primary" onClick={handleComplete}>Mark Completed</button>
          )}
          {!isNew && wo.status === "completed" && isDispatchRole && (
            <button className="btn-primary" onClick={handleConvertToInvoice}>Convert to Invoice</button>
          )}
          {!isNew && !["completed", "invoiced", "cancelled"].includes(wo.status) && isDispatchRole && (
            <button className="btn-danger" onClick={handleCancel}>Cancel</button>
          )}
          {!isNew && wo.converted_invoice_id && (
            <Link className="btn-secondary" to={`/invoices/${wo.converted_invoice_id}`}>View Invoice</Link>
          )}
        </div>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {!isNew && <span className={`badge badge-${wo.status}`}>{wo.status.replace(/_/g, " ")}</span>}

      <form className="card form-grid" onSubmit={handleSave}>
        {isNew ? (
          <label>
            Customer *
            <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
              <option value="">Select a customer...</option>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.display_name}</option>)}
            </select>
          </label>
        ) : (
          <div><strong>Customer:</strong> {wo.customer_name}</div>
        )}

        {isDispatchRole && (
          <div className="form-row">
            <label>
              Assigned Technician
              <select value={assignedTo} disabled={!editable} onChange={(e) => setAssignedTo(e.target.value)}>
                <option value="">Unassigned</option>
                {technicians.map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}
              </select>
            </label>
            <label>
              Scheduled Date
              <input type="date" value={scheduledDate} disabled={!editable} onChange={(e) => setScheduledDate(e.target.value)} />
            </label>
            {projectManagerEnabled && (
              <label>
                Project
                <select value={projectId} disabled={!editable} onChange={(e) => setProjectId(e.target.value)}>
                  <option value="">No project</option>
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.project_number} - {p.name}</option>)}
                </select>
              </label>
            )}
          </div>
        )}

        <label>
          Problem Description
          <textarea value={problemDescription} disabled={!editable} onChange={(e) => setProblemDescription(e.target.value)} rows={2} />
        </label>

        <table className="data-table line-items">
          <thead>
            <tr>
              <th>Type</th>
              {items.length > 0 && <th>Item</th>}
              <th>Description</th><th>GL Account</th><th>Qty/Hrs</th><th>Rate/Price</th><th>Amount</th>{editable && <th></th>}
            </tr>
          </thead>
          <tbody>
            {lines.map((l, idx) => (
              <tr key={idx}>
                <td>{l.line_type === "labor" ? "Labor" : "Part"}</td>
                {items.length > 0 && (
                  <td>
                    {l.line_type === "part" ? (
                      <select value={l.item_id || ""} disabled={!editable} onChange={(e) => applyItem(idx, e.target.value)}>
                        <option value="">Custom line</option>
                        {items.map((it) => <option key={it.id} value={it.id}>{it.sku} - {it.name}</option>)}
                      </select>
                    ) : "-"}
                  </td>
                )}
                <td>
                  <input value={l.description} disabled={!editable} onChange={(e) => updateLine(idx, "description", e.target.value)} placeholder="Description" />
                </td>
                <td>
                  <select value={l.account_id || ""} disabled={!editable} onChange={(e) => updateLine(idx, "account_id", e.target.value)}>
                    <option value="">Uncategorized</option>
                    {accounts.map((a) => <option key={a.id} value={a.id}>{a.code} {a.name}</option>)}
                  </select>
                </td>
                <td>
                  <input type="number" step="0.01" value={l.quantity} disabled={!editable} onChange={(e) => updateLine(idx, "quantity", e.target.value)} style={{ width: "70px" }} />
                </td>
                <td>
                  <input type="number" step="0.01" value={l.unit_price} disabled={!editable} onChange={(e) => updateLine(idx, "unit_price", e.target.value)} style={{ width: "90px" }} />
                </td>
                <td>${((parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0)).toFixed(2)}</td>
                {editable && <td><button type="button" className="btn-link" onClick={() => removeLine(idx)}>Remove</button></td>}
              </tr>
            ))}
          </tbody>
        </table>

        {editable && (
          <div className="button-row">
            <button type="button" className="btn-secondary" onClick={() => addLine("labor")}>Add Labor</button>
            <button type="button" className="btn-secondary" onClick={() => addLine("part")}>Add Part</button>
          </div>
        )}

        <div className="invoice-totals">
          <div className="total-line">Subtotal: ${subtotal.toFixed(2)}</div>
        </div>

        <label>
          Memo
          <textarea value={memo} disabled={!editable} onChange={(e) => setMemo(e.target.value)} rows={2} />
        </label>

        {editable && (
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving..." : isNew ? "Create Work Order" : "Save Changes"}
          </button>
        )}
      </form>
    </div>
  );
}

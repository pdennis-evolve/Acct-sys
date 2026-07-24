import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";

const PROJECT_STATUSES = ["planning", "active", "on_hold", "completed", "cancelled"];
const TASK_STATUSES = ["todo", "in_progress", "blocked", "done"];

const BLANK_TASK = { name: "", estimated_hours: 0, due_date: "", is_milestone: false, assigned_to: "" };
const BLANK_ENTRY = { hours: "", hourly_rate: "", entry_date: new Date().toISOString().slice(0, 10), memo: "", task_id: "", billable: true };

export default function ProjectDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();
  const canManage = hasRole("owner_admin", "project_manager");

  const [project, setProject] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [staff, setStaff] = useState([]);
  const [budget, setBudget] = useState(null);
  const [timeEntries, setTimeEntries] = useState([]);
  const [workOrders, setWorkOrders] = useState([]);
  const [bills, setBills] = useState([]);
  const [selectedEntryIds, setSelectedEntryIds] = useState([]);

  const [form, setForm] = useState({
    name: "", description: "", customer_id: "", project_manager_id: "",
    start_date: "", end_date: "", budget_hours: 0, budget_amount: 0,
  });
  const [newTask, setNewTask] = useState(BLANK_TASK);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [newEntry, setNewEntry] = useState(BLANK_ENTRY);

  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [billError, setBillError] = useState("");

  useEffect(() => {
    if (canManage) {
      client.get("/customers").then((res) => setCustomers(res.data.customers));
      client.get("/projects/staff").then((res) => setStaff(res.data.staff));
    }
    if (isNew) return;
    load();
  }, [id, isNew]);

  function load() {
    setLoading(true);
    client.get(`/projects/${id}`).then((res) => {
      const p = res.data.project;
      setProject(p);
      setForm({
        name: p.name, description: p.description || "", customer_id: p.customer_id || "",
        project_manager_id: p.project_manager_id || "", start_date: p.start_date || "",
        end_date: p.end_date || "", budget_hours: p.budget_hours, budget_amount: p.budget_amount,
      });
      setLoading(false);
    });
    client.get(`/projects/${id}/budget`).then((res) => setBudget(res.data.budget));
    client.get(`/projects/${id}/time-entries`).then((res) => setTimeEntries(res.data.time_entries));
    client.get("/work-orders", { params: { project_id: id } }).then((res) => setWorkOrders(res.data.work_orders));
    client.get("/bills", { params: { project_id: id } }).then((res) => setBills(res.data.bills));
  }

  async function handleSave(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (isNew) {
        const res = await client.post("/projects", form);
        navigate(`/projects/${res.data.project.id}`);
      } else {
        const res = await client.patch(`/projects/${id}`, form);
        setProject((p) => ({ ...p, ...res.data.project }));
      }
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(status) {
    const res = await client.patch(`/projects/${id}`, { status });
    setProject(res.data.project);
  }

  async function handleAddTask(e) {
    e.preventDefault();
    const res = await client.post(`/projects/${id}/tasks`, newTask);
    setProject((p) => ({ ...p, tasks: [...p.tasks, res.data.task] }));
    setNewTask(BLANK_TASK);
    setShowTaskForm(false);
  }

  async function handleTaskStatus(task, status) {
    const res = await client.patch(`/projects/${id}/tasks/${task.id}`, { status });
    setProject((p) => ({ ...p, tasks: p.tasks.map((t) => (t.id === task.id ? res.data.task : t)) }));
  }

  async function handleDeleteTask(task) {
    if (!confirm(`Delete task "${task.name}"?`)) return;
    await client.delete(`/projects/${id}/tasks/${task.id}`);
    setProject((p) => ({ ...p, tasks: p.tasks.filter((t) => t.id !== task.id) }));
  }

  async function handleLogTime(e) {
    e.preventDefault();
    const payload = { ...newEntry, task_id: newEntry.task_id || null };
    const res = await client.post(`/projects/${id}/time-entries`, payload);
    setTimeEntries((es) => [res.data.time_entry, ...es]);
    setNewEntry(BLANK_ENTRY);
  }

  async function handleDeleteEntry(entry) {
    await client.delete(`/projects/${id}/time-entries/${entry.id}`);
    setTimeEntries((es) => es.filter((e) => e.id !== entry.id));
  }

  function toggleEntrySelected(entryId) {
    setSelectedEntryIds((ids) => (ids.includes(entryId) ? ids.filter((i) => i !== entryId) : [...ids, entryId]));
  }

  async function handleBillTime() {
    setBillError("");
    try {
      const res = await client.post(`/projects/${id}/bill-time`, { time_entry_ids: selectedEntryIds });
      setSelectedEntryIds([]);
      load();
      navigate(`/invoices/${res.data.invoice.id}`);
    } catch (err) {
      setBillError(err.response?.data?.error || "Could not bill selected time");
    }
  }

  if (loading) return <div className="page-loading">Loading...</div>;

  const unbilledBillable = timeEntries.filter((e) => !e.billed && e.billable);

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New Project" : `${project.project_number} - ${project.name}`}</h1>
        <Link to="/projects" className="btn-link">Back to projects</Link>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {!isNew && (
        <div className="button-row" style={{ marginBottom: "1rem" }}>
          <span className={`badge badge-${project.status}`}>{project.status.replace(/_/g, " ")}</span>
          {canManage && PROJECT_STATUSES.filter((s) => s !== project.status).map((s) => (
            <button key={s} type="button" className="btn-secondary" onClick={() => handleStatusChange(s)}>
              Mark {s.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      )}

      <form className="card form-grid" onSubmit={handleSave}>
        <label>
          Name *
          <input value={form.name} disabled={!canManage} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </label>
        <label>
          Description
          <textarea value={form.description} disabled={!canManage} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
        </label>
        <div className="form-row">
          <label>
            Customer
            <select value={form.customer_id} disabled={!canManage} onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
              <option value="">No customer (internal)</option>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.display_name}</option>)}
            </select>
          </label>
          <label>
            Project Manager
            <select value={form.project_manager_id} disabled={!canManage} onChange={(e) => setForm({ ...form, project_manager_id: e.target.value })}>
              <option value="">Unassigned</option>
              {staff.map((s) => <option key={s.id} value={s.id}>{s.full_name}</option>)}
            </select>
          </label>
        </div>
        <div className="form-row">
          <label>
            Start Date
            <input type="date" value={form.start_date} disabled={!canManage} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
          </label>
          <label>
            End Date
            <input type="date" value={form.end_date} disabled={!canManage} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
          </label>
        </div>
        <div className="form-row">
          <label>
            Budget Hours
            <input type="number" step="0.5" value={form.budget_hours} disabled={!canManage} onChange={(e) => setForm({ ...form, budget_hours: e.target.value })} />
          </label>
          <label>
            Budget Amount
            <input type="number" step="0.01" value={form.budget_amount} disabled={!canManage} onChange={(e) => setForm({ ...form, budget_amount: e.target.value })} />
          </label>
        </div>
        {canManage && (
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving..." : isNew ? "Create Project" : "Save Changes"}
          </button>
        )}
      </form>

      {!isNew && budget && (
        <div className="card">
          <h2>Budget vs. Actual</h2>
          <div className="form-row">
            <div>
              <strong>Hours:</strong> {budget.actual_hours} of {budget.budget_hours} budgeted
              {" "}({budget.hours_variance >= 0 ? budget.hours_variance : `${budget.hours_variance}`} remaining)
            </div>
            <div>
              <strong>Amount:</strong> ${budget.actual_amount} of ${budget.budget_amount} budgeted
              {" "}(${budget.amount_variance} remaining)
            </div>
          </div>
          <p className="text-muted">
            Labor ${budget.breakdown.labor_amount} + Work Orders ${budget.breakdown.work_order_amount} + Bills ${budget.breakdown.bill_amount}
          </p>
        </div>
      )}

      {!isNew && (
        <div className="card">
          <div className="page-header">
            <h2>Tasks</h2>
            {canManage && (
              <button type="button" className="btn-secondary" onClick={() => setShowTaskForm((s) => !s)}>
                {showTaskForm ? "Cancel" : "New Task"}
              </button>
            )}
          </div>

          {showTaskForm && (
            <form className="form-grid" onSubmit={handleAddTask} style={{ marginBottom: "1rem" }}>
              <label>
                Task Name *
                <input value={newTask.name} onChange={(e) => setNewTask({ ...newTask, name: e.target.value })} required />
              </label>
              <div className="form-row">
                <label>
                  Assignee
                  <select value={newTask.assigned_to} onChange={(e) => setNewTask({ ...newTask, assigned_to: e.target.value })}>
                    <option value="">Unassigned</option>
                    {staff.map((s) => <option key={s.id} value={s.id}>{s.full_name}</option>)}
                  </select>
                </label>
                <label>
                  Due Date
                  <input type="date" value={newTask.due_date} onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })} />
                </label>
                <label>
                  Est. Hours
                  <input type="number" step="0.5" value={newTask.estimated_hours} onChange={(e) => setNewTask({ ...newTask, estimated_hours: e.target.value })} style={{ width: "80px" }} />
                </label>
                <label className="module-toggle">
                  <input type="checkbox" checked={newTask.is_milestone} onChange={(e) => setNewTask({ ...newTask, is_milestone: e.target.checked })} />
                  Milestone
                </label>
              </div>
              <button type="submit" className="btn-primary">Add Task</button>
            </form>
          )}

          <table className="data-table">
            <thead>
              <tr><th></th><th>Task</th><th>Status</th><th>Assignee</th><th>Due</th><th>Est. Hrs</th><th></th></tr>
            </thead>
            <tbody>
              {project.tasks.map((t) => {
                const canEditStatus = canManage || t.assigned_to === user?.id;
                return (
                  <tr key={t.id}>
                    <td>{t.is_milestone ? "★" : ""}</td>
                    <td>{t.name}</td>
                    <td>
                      <select
                        value={t.status}
                        disabled={!canEditStatus}
                        onChange={(e) => handleTaskStatus(t, e.target.value)}
                      >
                        {TASK_STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                      </select>
                    </td>
                    <td>{t.assignee_name || "Unassigned"}</td>
                    <td>{t.due_date || "-"}</td>
                    <td>{t.estimated_hours}</td>
                    <td>{canManage && <button type="button" className="btn-link" onClick={() => handleDeleteTask(t)}>Delete</button>}</td>
                  </tr>
                );
              })}
              {project.tasks.length === 0 && <tr><td colSpan={7} className="empty-row">No tasks yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {!isNew && (
        <div className="card">
          <h2>Time Entries</h2>

          <form className="form-grid" onSubmit={handleLogTime} style={{ marginBottom: "1rem" }}>
            <div className="form-row">
              <label>
                Date
                <input type="date" value={newEntry.entry_date} onChange={(e) => setNewEntry({ ...newEntry, entry_date: e.target.value })} required />
              </label>
              <label>
                Task
                <select value={newEntry.task_id} onChange={(e) => setNewEntry({ ...newEntry, task_id: e.target.value })}>
                  <option value="">General (no task)</option>
                  {project.tasks.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </label>
              <label>
                Hours
                <input type="number" step="0.25" value={newEntry.hours} onChange={(e) => setNewEntry({ ...newEntry, hours: e.target.value })} required style={{ width: "80px" }} />
              </label>
              <label>
                Rate ($/hr)
                <input type="number" step="0.01" value={newEntry.hourly_rate} onChange={(e) => setNewEntry({ ...newEntry, hourly_rate: e.target.value })} style={{ width: "90px" }} />
              </label>
              <label className="module-toggle">
                <input type="checkbox" checked={newEntry.billable} onChange={(e) => setNewEntry({ ...newEntry, billable: e.target.checked })} />
                Billable
              </label>
            </div>
            <label>
              Memo
              <input value={newEntry.memo} onChange={(e) => setNewEntry({ ...newEntry, memo: e.target.value })} placeholder="What did you work on?" />
            </label>
            <button type="submit" className="btn-primary">Log Time</button>
          </form>

          {billError && <div className="auth-error">{billError}</div>}

          {canManage && unbilledBillable.length > 0 && (
            <button type="button" className="btn-primary" disabled={selectedEntryIds.length === 0} onClick={handleBillTime} style={{ marginBottom: "0.75rem" }}>
              Bill Selected Time ({selectedEntryIds.length})
            </button>
          )}

          <table className="data-table">
            <thead>
              <tr>
                {canManage && <th></th>}
                <th>Date</th><th>User</th><th>Memo</th><th>Hours</th><th>Rate</th><th>Amount</th><th>Billable</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              {timeEntries.map((e) => (
                <tr key={e.id}>
                  {canManage && (
                    <td>
                      {!e.billed && e.billable && (
                        <input type="checkbox" checked={selectedEntryIds.includes(e.id)} onChange={() => toggleEntrySelected(e.id)} />
                      )}
                    </td>
                  )}
                  <td>{e.entry_date}</td>
                  <td>{e.user_name}</td>
                  <td>{e.memo || "-"}</td>
                  <td>{e.hours}</td>
                  <td>${e.hourly_rate}</td>
                  <td>${e.amount}</td>
                  <td>{e.billable ? "Yes" : "No"}</td>
                  <td>{e.billed ? <span className="badge badge-paid">Billed</span> : <span className="badge badge-draft">Unbilled</span>}</td>
                  <td>
                    {!e.billed && (
                      <button type="button" className="btn-link" onClick={() => handleDeleteEntry(e)}>Delete</button>
                    )}
                  </td>
                </tr>
              ))}
              {timeEntries.length === 0 && <tr><td colSpan={9} className="empty-row">No time logged yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {!isNew && workOrders.length > 0 && (
        <div className="card">
          <h2>Linked Work Orders</h2>
          <table className="data-table">
            <thead><tr><th>WO #</th><th>Status</th><th>Subtotal</th></tr></thead>
            <tbody>
              {workOrders.map((w) => (
                <tr key={w.id}>
                  <td><Link to={`/work-orders/${w.id}`}>{w.wo_number}</Link></td>
                  <td><span className={`badge badge-${w.status}`}>{w.status.replace(/_/g, " ")}</span></td>
                  <td>${w.subtotal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isNew && bills.length > 0 && (
        <div className="card">
          <h2>Linked Bills</h2>
          <table className="data-table">
            <thead><tr><th>Bill</th><th>Status</th><th>Total</th></tr></thead>
            <tbody>
              {bills.map((b) => (
                <tr key={b.id}>
                  <td><Link to={`/bills/${b.id}`}>{b.bill_number || b.id.slice(0, 8)}</Link></td>
                  <td><span className={`badge badge-${b.status}`}>{b.status.replace(/_/g, " ")}</span></td>
                  <td>${b.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

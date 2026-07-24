import { useEffect, useState } from "react";
import client from "../../api/client";

const ROLES = [
  "owner_admin", "accountant", "sales_ar_clerk", "warehouse_inventory",
  "dispatcher", "technician", "project_manager", "read_only_auditor",
];

export default function UserList() {
  const [users, setUsers] = useState([]);
  const [seatInfo, setSeatInfo] = useState({ seats_used: 0, seat_limit: 0 });
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "read_only_auditor" });
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/users").then((res) => {
      setUsers(res.data.users);
      setSeatInfo({ seats_used: res.data.seats_used, seat_limit: res.data.seat_limit });
    }).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/users", form);
      setForm({ email: "", password: "", full_name: "", role: "read_only_auditor" });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    }
  }

  async function toggleActive(user) {
    await client.patch(`/users/${user.id}`, { is_active: !user.is_active });
    load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>Users</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New User"}
        </button>
      </div>

      <p className="text-muted">{seatInfo.seats_used} of {seatInfo.seat_limit} seats used</p>

      {showForm && (
        <form className="card form-grid" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="form-row">
            <label>
              Full Name *
              <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
            </label>
            <label>
              Email *
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            </label>
            <label>
              Password *
              <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
            </label>
            <label>
              Role
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {ROLES.map((r) => <option key={r} value={r}>{r.replace(/_/g, " ")}</option>)}
              </select>
            </label>
          </div>
          <button type="submit" className="btn-primary">Create User</button>
        </form>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>{u.role.replace(/_/g, " ")}</td>
                <td><span className={`badge ${u.is_active ? "badge-active" : "badge-inactive"}`}>{u.is_active ? "Active" : "Inactive"}</span></td>
                <td><button className="btn-link" onClick={() => toggleActive(u)}>{u.is_active ? "Deactivate" : "Activate"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";

const STATUSES = ["", "planning", "active", "on_hold", "completed", "cancelled"];

export default function ProjectList() {
  const { hasRole } = useAuth();
  const [projects, setProjects] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const canManage = hasRole("owner_admin", "project_manager");

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (status) params.status = status;
    client.get("/projects", { params }).then((res) => setProjects(res.data.projects)).finally(() => setLoading(false));
  }, [status]);

  return (
    <div>
      <div className="page-header">
        <h1>Projects</h1>
        {canManage && <Link to="/projects/new" className="btn-primary">New Project</Link>}
      </div>

      <div className="filter-bar">
        {STATUSES.map((s) => (
          <button key={s || "all"} className={`filter-chip ${status === s ? "active" : ""}`} onClick={() => setStatus(s)}>
            {s ? s.replace(/_/g, " ") : "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Project #</th><th>Name</th><th>Customer</th><th>Status</th><th>Manager</th><th>Budget</th></tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td><Link to={`/projects/${p.id}`}>{p.project_number}</Link></td>
                <td>{p.name}</td>
                <td>{p.customer_name || "-"}</td>
                <td><span className={`badge badge-${p.status}`}>{p.status.replace(/_/g, " ")}</span></td>
                <td>{p.project_manager_name || "Unassigned"}</td>
                <td>${p.budget_amount}</td>
              </tr>
            ))}
            {projects.length === 0 && <tr><td colSpan={6} className="empty-row">No projects found.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

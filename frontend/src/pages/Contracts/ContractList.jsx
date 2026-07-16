import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

const STATUSES = ["", "draft", "active", "expired", "terminated", "renewed"];

export default function ContractList() {
  const [contracts, setContracts] = useState([]);
  const [expiring, setExpiring] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      client.get("/contracts", { params: status ? { status } : {} }),
      client.get("/contracts", { params: { expiring_within_days: 30 } }),
    ]).then(([listRes, expiringRes]) => {
      setContracts(listRes.data.contracts);
      setExpiring(expiringRes.data.contracts);
    }).finally(() => setLoading(false));
  }, [status]);

  return (
    <div>
      <div className="page-header">
        <h1>Contracts</h1>
        <Link to="/contracts/new" className="btn-primary">New Contract</Link>
      </div>

      {expiring.length > 0 && (
        <div className="card" style={{ borderColor: "var(--color-warning)", background: "#fff9ec" }}>
          <h2 style={{ marginTop: 0 }}>⚠ {expiring.length} Contract{expiring.length > 1 ? "s" : ""} Expiring Within 30 Days</h2>
          <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
            {expiring.map((c) => (
              <li key={c.id}>
                <Link to={`/contracts/${c.id}`}>{c.title}</Link> ({c.customer_name}) &mdash; expires {c.end_date}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="filter-bar">
        {STATUSES.map((s) => (
          <button key={s || "all"} className={`filter-chip ${status === s ? "active" : ""}`} onClick={() => setStatus(s)}>
            {s || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Title</th><th>Customer</th><th>Status</th><th>Start</th><th>End</th><th>Renewal</th></tr>
          </thead>
          <tbody>
            {contracts.map((c) => (
              <tr key={c.id}>
                <td><Link to={`/contracts/${c.id}`}>{c.title}</Link></td>
                <td>{c.customer_name}</td>
                <td>
                  <span className={`badge badge-${c.status}`}>{c.status}</span>
                  {c.is_expired && <span className="badge badge-cancelled" style={{ marginLeft: "0.3rem" }}>Expired</span>}
                  {c.is_expiring_soon && <span className="badge badge-sent" style={{ marginLeft: "0.3rem" }}>Expiring Soon</span>}
                </td>
                <td>{c.start_date || "-"}</td>
                <td>{c.end_date || "-"}</td>
                <td>{c.renewal_date || "-"}</td>
              </tr>
            ))}
            {contracts.length === 0 && <tr><td colSpan={6} className="empty-row">No contracts yet.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

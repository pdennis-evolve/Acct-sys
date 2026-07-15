import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

export default function CustomerList() {
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  function load(q) {
    setLoading(true);
    client
      .get("/customers", { params: q ? { q } : {} })
      .then((res) => setCustomers(res.data.customers))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  function handleSearch(e) {
    e.preventDefault();
    load(search);
  }

  return (
    <div>
      <div className="page-header">
        <h1>Customers</h1>
        <Link to="/customers/new" className="btn-primary">New Customer</Link>
      </div>

      <form className="search-bar" onSubmit={handleSearch}>
        <input placeholder="Search customers..." value={search} onChange={(e) => setSearch(e.target.value)} />
        <button type="submit" className="btn-secondary">Search</button>
      </form>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Company</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td><Link to={`/customers/${c.id}`}>{c.display_name}</Link></td>
                <td>{c.company_name || "-"}</td>
                <td>{c.email || "-"}</td>
                <td>{c.phone || "-"}</td>
                <td><span className={`badge ${c.is_active ? "badge-active" : "badge-inactive"}`}>{c.is_active ? "Active" : "Inactive"}</span></td>
              </tr>
            ))}
            {customers.length === 0 && (
              <tr><td colSpan={5} className="empty-row">No customers yet.</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

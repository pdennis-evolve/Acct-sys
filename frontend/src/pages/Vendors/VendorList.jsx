import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

export default function VendorList() {
  const [vendors, setVendors] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  function load(q) {
    setLoading(true);
    client
      .get("/vendors", { params: q ? { q } : {} })
      .then((res) => setVendors(res.data.vendors))
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
        <h1>Vendors</h1>
        <Link to="/vendors/new" className="btn-primary">New Vendor</Link>
      </div>

      <form className="search-bar" onSubmit={handleSearch}>
        <input placeholder="Search vendors..." value={search} onChange={(e) => setSearch(e.target.value)} />
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
            {vendors.map((v) => (
              <tr key={v.id}>
                <td><Link to={`/vendors/${v.id}`}>{v.display_name}</Link></td>
                <td>{v.company_name || "-"}</td>
                <td>{v.email || "-"}</td>
                <td>{v.phone || "-"}</td>
                <td><span className={`badge ${v.is_active ? "badge-active" : "badge-inactive"}`}>{v.is_active ? "Active" : "Inactive"}</span></td>
              </tr>
            ))}
            {vendors.length === 0 && (
              <tr><td colSpan={5} className="empty-row">No vendors yet.</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

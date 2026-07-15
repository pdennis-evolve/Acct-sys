import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";

const TYPE_LABELS = { inventory: "Inventory", non_inventory: "Non-Inventory", service: "Service" };

export default function ItemList() {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    const params = {};
    if (search) params.q = search;
    if (lowStockOnly) params.low_stock = "true";
    client.get("/items", { params }).then((res) => setItems(res.data.items)).finally(() => setLoading(false));
  }

  useEffect(load, [lowStockOnly]);

  function handleSearch(e) {
    e.preventDefault();
    load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>Items</h1>
        <Link to="/items/new" className="btn-primary">New Item</Link>
      </div>

      <form className="search-bar" onSubmit={handleSearch}>
        <input placeholder="Search by SKU or name..." value={search} onChange={(e) => setSearch(e.target.value)} />
        <button type="submit" className="btn-secondary">Search</button>
      </form>

      <div className="filter-bar">
        <button className={`filter-chip ${!lowStockOnly ? "active" : ""}`} onClick={() => setLowStockOnly(false)}>All Items</button>
        <button className={`filter-chip ${lowStockOnly ? "active" : ""}`} onClick={() => setLowStockOnly(true)}>Low Stock Only</button>
      </div>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Name</th>
              <th>Type</th>
              <th>Unit Cost</th>
              <th>Unit Price</th>
              <th>On Hand</th>
              <th>Reorder Point</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td><Link to={`/items/${i.id}`}>{i.sku}</Link></td>
                <td>{i.name}</td>
                <td>{TYPE_LABELS[i.item_type]}</td>
                <td>${i.unit_cost}</td>
                <td>${i.unit_price}</td>
                <td>{i.tracks_inventory ? i.quantity_on_hand : "-"}</td>
                <td>{i.tracks_inventory ? i.reorder_point : "-"}</td>
                <td>
                  {i.tracks_inventory && i.below_reorder_point && <span className="badge badge-sent">Low Stock</span>}
                  {!i.is_active && <span className="badge badge-inactive">Inactive</span>}
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="empty-row">No items found.</td></tr>}
          </tbody>
        </table>
      )}
    </div>
  );
}

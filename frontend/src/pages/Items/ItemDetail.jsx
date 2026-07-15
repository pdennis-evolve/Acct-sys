import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import client from "../../api/client";

const BLANK = {
  sku: "", name: "", description: "", item_type: "inventory",
  unit_cost: 0, unit_price: 0, reorder_point: 0, reorder_quantity: 0,
  income_account_id: "", expense_account_id: "",
};

export default function ItemDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();

  const [item, setItem] = useState(null);
  const [form, setForm] = useState(BLANK);
  const [openingQty, setOpeningQty] = useState("");
  const [accounts, setAccounts] = useState([]);
  const [locations, setLocations] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [showAdjust, setShowAdjust] = useState(false);
  const [adjustForm, setAdjustForm] = useState({ quantity_delta: "", location_id: "", memo: "" });

  function loadItem() {
    if (isNew) {
      setItem(null);
      setForm(BLANK);
      setLoading(false);
      return;
    }
    setLoading(true);
    client.get(`/items/${id}`).then((res) => {
      const i = res.data.item;
      setItem(i);
      setForm({
        sku: i.sku, name: i.name, description: i.description || "", item_type: i.item_type,
        unit_cost: i.unit_cost, unit_price: i.unit_price, reorder_point: i.reorder_point,
        reorder_quantity: i.reorder_quantity, income_account_id: i.income_account_id || "",
        expense_account_id: i.expense_account_id || "",
      });
      setLoading(false);
    });
    client.get(`/items/${id}/ledger`).then((res) => setLedger(res.data.transactions));
  }

  useEffect(() => {
    client.get("/accounts").then((res) => setAccounts(res.data.accounts));
    client.get("/locations").then((res) => setLocations(res.data.locations));
    loadItem();
  }, [id, isNew]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (isNew) {
        const payload = { ...form };
        if (form.item_type === "inventory" && openingQty) payload.opening_quantity = openingQty;
        const res = await client.post("/items", payload);
        navigate(`/items/${res.data.item.id}`);
      } else {
        const res = await client.patch(`/items/${id}`, form);
        setItem((prev) => ({ ...prev, ...res.data.item }));
      }
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleAdjust(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post(`/items/${id}/adjust`, adjustForm);
      setAdjustForm({ quantity_delta: "", location_id: "", memo: "" });
      setShowAdjust(false);
      loadItem();
    } catch (err) {
      setError(err.response?.data?.error || "Adjustment failed");
    }
  }

  if (loading || (!isNew && !item)) return <div className="page-loading">Loading...</div>;

  const incomeAccounts = accounts.filter((a) => a.type === "income");
  const expenseAccounts = accounts.filter((a) => a.type === "expense");

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New Item" : `${item.sku} - ${item.name}`}</h1>
        <Link to="/items" className="btn-link">Back to items</Link>
      </div>

      {error && <div className="auth-error">{error}</div>}

      <form className="card form-grid" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            SKU *
            <input value={form.sku} disabled={!isNew} onChange={(e) => setForm({ ...form, sku: e.target.value })} required />
          </label>
          <label>
            Name *
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Type
            <select value={form.item_type} disabled={!isNew} onChange={(e) => setForm({ ...form, item_type: e.target.value })}>
              <option value="inventory">Inventory</option>
              <option value="non_inventory">Non-Inventory</option>
              <option value="service">Service</option>
            </select>
          </label>
        </div>

        <label>
          Description
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
        </label>

        <div className="form-row">
          <label>
            Unit Cost
            <input type="number" step="0.01" value={form.unit_cost} onChange={(e) => setForm({ ...form, unit_cost: e.target.value })} />
          </label>
          <label>
            Unit Price
            <input type="number" step="0.01" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: e.target.value })} />
          </label>
        </div>

        {form.item_type === "inventory" && (
          <div className="form-row">
            <label>
              Reorder Point
              <input type="number" value={form.reorder_point} onChange={(e) => setForm({ ...form, reorder_point: e.target.value })} />
            </label>
            <label>
              Reorder Quantity
              <input type="number" value={form.reorder_quantity} onChange={(e) => setForm({ ...form, reorder_quantity: e.target.value })} />
            </label>
            {isNew && (
              <label>
                Opening Quantity
                <input type="number" value={openingQty} onChange={(e) => setOpeningQty(e.target.value)} placeholder="0" />
              </label>
            )}
          </div>
        )}

        <div className="form-row">
          <label>
            Income Account
            <select value={form.income_account_id} onChange={(e) => setForm({ ...form, income_account_id: e.target.value })}>
              <option value="">None</option>
              {incomeAccounts.map((a) => <option key={a.id} value={a.id}>{a.code} {a.name}</option>)}
            </select>
          </label>
          <label>
            Expense/COGS Account
            <select value={form.expense_account_id} onChange={(e) => setForm({ ...form, expense_account_id: e.target.value })}>
              <option value="">None</option>
              {expenseAccounts.map((a) => <option key={a.id} value={a.id}>{a.code} {a.name}</option>)}
            </select>
          </label>
        </div>

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving..." : isNew ? "Create Item" : "Save Changes"}
        </button>
      </form>

      {!isNew && item?.tracks_inventory && (
        <>
          <div className="card">
            <div className="page-header">
              <h2>Stock by Location</h2>
              <button type="button" className="btn-secondary" onClick={() => setShowAdjust((s) => !s)}>
                {showAdjust ? "Cancel" : "Adjust Stock"}
              </button>
            </div>

            {showAdjust && (
              <form className="form-grid" onSubmit={handleAdjust} style={{ marginBottom: "1rem" }}>
                <div className="form-row">
                  <label>
                    Location
                    <select value={adjustForm.location_id} onChange={(e) => setAdjustForm({ ...adjustForm, location_id: e.target.value })}>
                      <option value="">Default location</option>
                      {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                    </select>
                  </label>
                  <label>
                    Quantity Change (+/-)
                    <input type="number" step="0.01" value={adjustForm.quantity_delta} onChange={(e) => setAdjustForm({ ...adjustForm, quantity_delta: e.target.value })} required />
                  </label>
                  <label>
                    Memo
                    <input value={adjustForm.memo} onChange={(e) => setAdjustForm({ ...adjustForm, memo: e.target.value })} placeholder="Cycle count, damage, etc." />
                  </label>
                </div>
                <button type="submit" className="btn-primary">Record Adjustment</button>
              </form>
            )}

            <table className="data-table">
              <thead><tr><th>Location</th><th>Quantity On Hand</th></tr></thead>
              <tbody>
                {item.stock_by_location.map((s) => (
                  <tr key={s.location_id}>
                    <td>{s.location_name}</td>
                    <td>{s.quantity_on_hand}</td>
                  </tr>
                ))}
                {item.stock_by_location.length === 0 && <tr><td colSpan={2} className="empty-row">No stock recorded yet.</td></tr>}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h2>Recent Activity</h2>
            <table className="data-table">
              <thead><tr><th>Date</th><th>Type</th><th>Qty Change</th><th>Reference</th><th>Memo</th></tr></thead>
              <tbody>
                {ledger.map((t) => (
                  <tr key={t.id}>
                    <td>{t.txn_date}</td>
                    <td>{t.txn_type}</td>
                    <td className={parseFloat(t.quantity_delta) >= 0 ? "amount-positive" : "amount-negative"}>
                      {parseFloat(t.quantity_delta) >= 0 ? "+" : ""}{t.quantity_delta}
                    </td>
                    <td>{t.reference_type || "-"}</td>
                    <td>{t.memo || "-"}</td>
                  </tr>
                ))}
                {ledger.length === 0 && <tr><td colSpan={5} className="empty-row">No activity yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

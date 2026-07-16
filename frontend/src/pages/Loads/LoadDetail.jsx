import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import ShipmentPanel from "../../components/ShipmentPanel";

const BLANK_CHARGE = () => ({ description: "", amount: 0 });

export default function LoadDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const { hasModule } = useAuth();

  const [load, setLoad] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [customerId, setCustomerId] = useState("");
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [pickupDate, setPickupDate] = useState("");
  const [baseRate, setBaseRate] = useState(0);
  const [charges, setCharges] = useState([]);
  const [memo, setMemo] = useState("");
  const [driverId, setDriverId] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function loadDetail() {
    if (isNew) {
      setLoad(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    client.get(`/loads/${id}`).then((res) => {
      const l = res.data.load;
      setLoad(l);
      setOrigin(l.origin || "");
      setDestination(l.destination || "");
      setPickupDate(l.pickup_date || "");
      setBaseRate(l.base_rate);
      setCharges(l.charges);
      setMemo(l.memo || "");
      setDriverId(l.driver_id || "");
      setVehicleId(l.vehicle_id || "");
      setLoading(false);
    });
  }

  useEffect(() => {
    client.get("/customers").then((res) => setCustomers(res.data.customers));
    client.get("/drivers").then((res) => setDrivers(res.data.drivers.filter((d) => d.status === "active")));
    client.get("/vehicles").then((res) => setVehicles(res.data.vehicles.filter((v) => v.status === "active")));
    loadDetail();
  }, [id, isNew]);

  function updateCharge(idx, field, value) {
    setCharges((cs) => cs.map((c, i) => (i === idx ? { ...c, [field]: value } : c)));
  }
  function addCharge() {
    setCharges((cs) => [...cs, BLANK_CHARGE()]);
  }
  function removeCharge(idx) {
    setCharges((cs) => cs.filter((_, i) => i !== idx));
  }

  const chargesTotal = charges.reduce((sum, c) => sum + (parseFloat(c.amount) || 0), 0);
  const total = (parseFloat(baseRate) || 0) + chargesTotal;

  async function handleSave(e) {
    e.preventDefault();
    setError("");
    if (isNew && !customerId) {
      setError("Please select a customer");
      return;
    }
    setSaving(true);
    try {
      const payload = { origin, destination, pickup_date: pickupDate || null, base_rate: baseRate, charges, memo };
      if (isNew) {
        payload.customer_id = customerId;
        const res = await client.post("/loads", payload);
        navigate(`/loads/${res.data.load.id}`);
      } else {
        const res = await client.patch(`/loads/${id}`, payload);
        setLoad(res.data.load);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSchedule() {
    setError("");
    if (!driverId || !vehicleId) {
      setError("Select a driver and vehicle to schedule this load");
      return;
    }
    try {
      const res = await client.post(`/loads/${id}/schedule`, { driver_id: driverId, vehicle_id: vehicleId, pickup_date: pickupDate || null });
      setLoad(res.data.load);
    } catch (err) {
      setError(err.response?.data?.error || "Schedule failed");
    }
  }
  async function handleDispatch() {
    const res = await client.post(`/loads/${id}/dispatch`);
    setLoad(res.data.load);
  }
  async function handleStartTransit() {
    const res = await client.post(`/loads/${id}/start-transit`);
    setLoad(res.data.load);
  }
  async function handleDeliver() {
    const res = await client.post(`/loads/${id}/deliver`, {});
    setLoad(res.data.load);
  }
  async function handleCancel() {
    if (!confirm("Cancel this load?")) return;
    const res = await client.post(`/loads/${id}/cancel`);
    setLoad(res.data.load);
  }
  async function handleConvertToInvoice() {
    const res = await client.post(`/loads/${id}/convert-to-invoice`);
    navigate(`/invoices/${res.data.invoice.id}`);
  }

  if (loading || (!isNew && !load)) return <div className="page-loading">Loading...</div>;

  const editable = isNew || (load && ["draft", "scheduled"].includes(load.status));

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New Load" : load.load_number}</h1>
        <div className="button-row">
          {!isNew && load.status === "draft" && <button className="btn-secondary" onClick={handleSchedule}>Assign & Schedule</button>}
          {!isNew && load.status === "scheduled" && <button className="btn-secondary" onClick={handleDispatch}>Dispatch</button>}
          {!isNew && load.status === "dispatched" && <button className="btn-secondary" onClick={handleStartTransit}>Start Transit</button>}
          {!isNew && load.status === "in_transit" && <button className="btn-primary" onClick={handleDeliver}>Mark Delivered</button>}
          {!isNew && load.status === "delivered" && <button className="btn-primary" onClick={handleConvertToInvoice}>Convert to Invoice</button>}
          {!isNew && !["delivered", "invoiced", "cancelled"].includes(load.status) && (
            <button className="btn-danger" onClick={handleCancel}>Cancel</button>
          )}
          {!isNew && load.converted_invoice_id && (
            <Link className="btn-secondary" to={`/invoices/${load.converted_invoice_id}`}>View Invoice</Link>
          )}
        </div>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {!isNew && <span className={`badge badge-${load.status}`}>{load.status.replace(/_/g, " ")}</span>}

      {!isNew && load.status === "draft" && (
        <div className="card">
          <h3 className="form-section-title" style={{ marginTop: 0 }}>Assign Driver &amp; Vehicle</h3>
          <div className="form-row">
            <label>
              Driver
              <select value={driverId} onChange={(e) => setDriverId(e.target.value)}>
                <option value="">Select a driver...</option>
                {drivers.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </select>
            </label>
            <label>
              Vehicle
              <select value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>
                <option value="">Select a vehicle...</option>
                {vehicles.map((v) => <option key={v.id} value={v.id}>{v.unit_number}</option>)}
              </select>
            </label>
          </div>
        </div>
      )}

      {!isNew && load.driver_name && (
        <p className="text-muted">Assigned: {load.driver_name} driving {load.vehicle_unit_number}</p>
      )}

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
          <div><strong>Customer:</strong> {load.customer_name}</div>
        )}

        <div className="form-row">
          <label>
            Origin
            <input value={origin} disabled={!editable} onChange={(e) => setOrigin(e.target.value)} placeholder="Chicago, IL" />
          </label>
          <label>
            Destination
            <input value={destination} disabled={!editable} onChange={(e) => setDestination(e.target.value)} placeholder="Dallas, TX" />
          </label>
          <label>
            Pickup Date
            <input type="date" value={pickupDate} disabled={!editable} onChange={(e) => setPickupDate(e.target.value)} />
          </label>
        </div>

        <label>
          Base Rate
          <input type="number" step="0.01" value={baseRate} disabled={!editable} onChange={(e) => setBaseRate(e.target.value)} style={{ width: "140px" }} />
        </label>

        <h3 className="form-section-title">Accessorial Charges</h3>
        <table className="data-table line-items">
          <thead><tr><th>Description</th><th>Amount</th>{editable && <th></th>}</tr></thead>
          <tbody>
            {charges.map((c, idx) => (
              <tr key={idx}>
                <td>
                  <input value={c.description} disabled={!editable} onChange={(e) => updateCharge(idx, "description", e.target.value)} placeholder="Fuel surcharge, detention, etc." />
                </td>
                <td>
                  <input type="number" step="0.01" value={c.amount} disabled={!editable} onChange={(e) => updateCharge(idx, "amount", e.target.value)} style={{ width: "100px" }} />
                </td>
                {editable && <td><button type="button" className="btn-link" onClick={() => removeCharge(idx)}>Remove</button></td>}
              </tr>
            ))}
            {charges.length === 0 && <tr><td colSpan={3} className="empty-row">No accessorial charges.</td></tr>}
          </tbody>
        </table>
        {editable && <button type="button" className="btn-secondary" onClick={addCharge}>Add Charge</button>}

        <div className="invoice-totals">
          <div className="total-line">Total: ${total.toFixed(2)}</div>
        </div>

        <label>
          Memo
          <textarea value={memo} disabled={!editable} onChange={(e) => setMemo(e.target.value)} rows={2} />
        </label>

        {editable && (
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving..." : isNew ? "Create Load" : "Save Changes"}
          </button>
        )}
      </form>

      {!isNew && hasModule("order_tracking") && (
        <ShipmentPanel referenceType="load" referenceId={id} />
      )}
    </div>
  );
}

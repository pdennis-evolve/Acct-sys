import { useEffect, useState } from "react";
import client from "../../api/client";
import { defaultRange } from "./reportUtils";

export default function IncomeReport() {
  const [range, setRange] = useState(defaultRange());
  const [groupBy, setGroupBy] = useState("day");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    client
      .get("/reports/income", { params: { ...range, group_by: groupBy } })
      .then((res) => setReport(res.data))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  function handleRun(e) {
    e.preventDefault();
    load();
  }

  return (
    <div>
      <h1>Income Report</h1>

      <form className="card filter-form" onSubmit={handleRun}>
        <div className="form-row">
          <label>
            Start Date
            <input type="date" value={range.start} onChange={(e) => setRange({ ...range, start: e.target.value })} />
          </label>
          <label>
            End Date
            <input type="date" value={range.end} onChange={(e) => setRange({ ...range, end: e.target.value })} />
          </label>
          <label>
            Group By
            <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
              <option value="day">Daily</option>
              <option value="month">Monthly</option>
            </select>
          </label>
        </div>
        <button type="submit" className="btn-primary">Run Report</button>
      </form>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : report ? (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-value">${report.totals.subtotal}</div>
              <div className="stat-label">Taxable Sales</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">${report.totals.tax}</div>
              <div className="stat-label">Tax Collected</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">${report.totals.total}</div>
              <div className="stat-label">Total Invoiced</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{report.totals.invoice_count}</div>
              <div className="stat-label">Invoices</div>
            </div>
          </div>

          <div className="card">
            <table className="data-table">
              <thead><tr><th>Period</th><th>Subtotal</th><th>Tax</th><th>Total</th><th>Invoices</th></tr></thead>
              <tbody>
                {report.periods.map((p) => (
                  <tr key={p.period}>
                    <td>{p.period}</td>
                    <td>${p.subtotal}</td>
                    <td>${p.tax}</td>
                    <td>${p.total}</td>
                    <td>{p.invoice_count}</td>
                  </tr>
                ))}
                {report.periods.length === 0 && <tr><td colSpan={5} className="empty-row">No invoices in this range.</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  );
}

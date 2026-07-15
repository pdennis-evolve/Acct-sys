import { useEffect, useState } from "react";
import client from "../../api/client";
import { defaultRange } from "./reportUtils";

export default function SalesTax() {
  const [range, setRange] = useState(defaultRange());
  const [groupBy, setGroupBy] = useState("none");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    client
      .get("/reports/sales-tax", { params: { ...range, group_by: groupBy } })
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
      <h1>Sales Tax Report</h1>
      <p className="text-muted">
        Tax collected on invoices, broken out by rate/jurisdiction. Use this to reconcile what's owed
        to each taxing authority for the period.
      </p>

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
              <option value="none">Summary</option>
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
              <div className="stat-value">${report.totals.taxable_sales}</div>
              <div className="stat-label">Taxable Sales</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">${report.totals.tax_collected}</div>
              <div className="stat-label">Tax Collected</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">${report.totals.total_sales}</div>
              <div className="stat-label">Total Sales (incl. tax)</div>
            </div>
          </div>

          <div className="card">
            <h2>By Tax Rate</h2>
            <table className="data-table">
              <thead><tr><th>Rate</th><th>Taxable Sales</th><th>Tax Collected</th><th>Total Sales</th></tr></thead>
              <tbody>
                {report.by_rate.map((r) => (
                  <tr key={r.key}>
                    <td>{r.label}</td>
                    <td>${r.taxable_sales}</td>
                    <td>${r.tax_collected}</td>
                    <td>${r.total_sales}</td>
                  </tr>
                ))}
                {report.by_rate.length === 0 && <tr><td colSpan={4} className="empty-row">No sales in this range.</td></tr>}
              </tbody>
            </table>
          </div>

          {report.periods && (
            <div className="card">
              <h2>By Period</h2>
              <table className="data-table">
                <thead><tr><th>Period</th><th>Taxable Sales</th><th>Tax Collected</th></tr></thead>
                <tbody>
                  {report.periods.map((p) => (
                    <tr key={p.period}>
                      <td>{p.period}</td>
                      <td>${p.taxable_sales}</td>
                      <td>${p.tax_collected}</td>
                    </tr>
                  ))}
                  {report.periods.length === 0 && <tr><td colSpan={3} className="empty-row">No sales in this range.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

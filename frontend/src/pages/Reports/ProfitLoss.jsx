import { useEffect, useState } from "react";
import client from "../../api/client";
import { defaultRange } from "./reportUtils";

export default function ProfitLoss() {
  const [range, setRange] = useState(defaultRange());
  const [groupBy, setGroupBy] = useState("none");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    client
      .get("/reports/profit-loss", { params: { ...range, group_by: groupBy } })
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
      <h1>Profit &amp; Loss</h1>

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
              <div className="stat-value">${report.income_total}</div>
              <div className="stat-label">Total Income</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">${report.expenses_total}</div>
              <div className="stat-label">Total Expenses</div>
            </div>
            <div className={`stat-card ${parseFloat(report.net_income) < 0 ? "stat-warning" : ""}`}>
              <div className="stat-value">${report.net_income}</div>
              <div className="stat-label">Net Income</div>
            </div>
          </div>

          {report.periods && (
            <div className="card">
              <h2>By Period</h2>
              <table className="data-table">
                <thead><tr><th>Period</th><th>Income</th><th>Expenses</th><th>Net Income</th></tr></thead>
                <tbody>
                  {report.periods.map((p) => (
                    <tr key={p.period}>
                      <td>{p.period}</td>
                      <td>${p.income}</td>
                      <td>${p.expenses}</td>
                      <td>${p.net_income}</td>
                    </tr>
                  ))}
                  {report.periods.length === 0 && <tr><td colSpan={4} className="empty-row">No activity in this range.</td></tr>}
                </tbody>
              </table>
            </div>
          )}

          <div className="card">
            <h2>Income by Account</h2>
            <table className="data-table">
              <thead><tr><th>Account</th><th>Amount</th></tr></thead>
              <tbody>
                {report.income.map((r) => (
                  <tr key={r.account_id || "uncategorized"}>
                    <td>{r.account_name}</td>
                    <td>${r.total}</td>
                  </tr>
                ))}
                {report.income.length === 0 && <tr><td colSpan={2} className="empty-row">No income in this range.</td></tr>}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h2>Expenses by Account</h2>
            <table className="data-table">
              <thead><tr><th>Account</th><th>Amount</th></tr></thead>
              <tbody>
                {report.expenses.map((r) => (
                  <tr key={r.account_id || "uncategorized"}>
                    <td>{r.account_name}</td>
                    <td>${r.total}</td>
                  </tr>
                ))}
                {report.expenses.length === 0 && <tr><td colSpan={2} className="empty-row">No expenses in this range.</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  );
}

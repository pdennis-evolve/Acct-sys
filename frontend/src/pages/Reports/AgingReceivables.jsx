import { useEffect, useState } from "react";
import client from "../../api/client";

const PRESETS = {
  "30/60/90": "30,60,90",
  "15/30/45": "15,30,45",
};

export default function AgingReceivables() {
  const [asOf, setAsOf] = useState(new Date().toISOString().slice(0, 10));
  const [ranges, setRanges] = useState("30,60,90");
  const [issueStart, setIssueStart] = useState("");
  const [issueEnd, setIssueEnd] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    const params = { as_of: asOf, ranges };
    if (issueStart) params.issue_start = issueStart;
    if (issueEnd) params.issue_end = issueEnd;
    client
      .get("/reports/aging-receivables", { params })
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
      <h1>Aging Receivables</h1>
      <p className="text-muted">Open invoice balances bucketed by days past due, as of a chosen date.</p>

      <form className="card filter-form" onSubmit={handleRun}>
        <div className="form-row">
          <label>
            As Of Date
            <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
          </label>
          <label>
            Bucket Sizes (days)
            <input value={ranges} onChange={(e) => setRanges(e.target.value)} placeholder="30,60,90" />
          </label>
        </div>
        <div className="filter-bar">
          {Object.entries(PRESETS).map(([label, value]) => (
            <button
              type="button"
              key={label}
              className={`filter-chip ${ranges === value ? "active" : ""}`}
              onClick={() => setRanges(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <h3 className="form-section-title">Custom Range (optional)</h3>
        <div className="form-row">
          <label>
            Issued On/After
            <input type="date" value={issueStart} onChange={(e) => setIssueStart(e.target.value)} />
          </label>
          <label>
            Issued On/Before
            <input type="date" value={issueEnd} onChange={(e) => setIssueEnd(e.target.value)} />
          </label>
        </div>
        <button type="submit" className="btn-primary">Run Report</button>
      </form>

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : report ? (
        <div className="card">
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  {report.buckets.map((b) => <th key={b}>{b}</th>)}
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {report.rows.map((row) => (
                  <tr key={row.customer_id}>
                    <td>{row.customer_name}</td>
                    {report.buckets.map((b) => <td key={b}>${row.amounts[b]}</td>)}
                    <td><strong>${row.total}</strong></td>
                  </tr>
                ))}
                {report.rows.length === 0 && (
                  <tr><td colSpan={report.buckets.length + 2} className="empty-row">No open invoices.</td></tr>
                )}
              </tbody>
              {report.rows.length > 0 && (
                <tfoot>
                  <tr>
                    <td><strong>Total</strong></td>
                    {report.buckets.map((b) => <td key={b}><strong>${report.totals[b]}</strong></td>)}
                    <td><strong>${report.grand_total}</strong></td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}

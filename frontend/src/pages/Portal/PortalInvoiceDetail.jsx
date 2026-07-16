import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import portalClient from "../../api/portalClient";

export default function PortalInvoiceDetail() {
  const { id } = useParams();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [payMessage, setPayMessage] = useState("");
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    setLoading(true);
    portalClient.get(`/invoices/${id}`).then((res) => setInvoice(res.data.invoice)).finally(() => setLoading(false));
  }, [id]);

  async function handleDownloadPdf() {
    const res = await portalClient.get(`/invoices/${id}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function handlePayNow() {
    setPaying(true);
    setPayMessage("");
    try {
      await portalClient.post(`/invoices/${id}/pay`);
    } catch (err) {
      setPayMessage(err.response?.data?.error || "Payment could not be processed.");
    } finally {
      setPaying(false);
    }
  }

  if (loading || !invoice) return <div className="page-loading">Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h1>{invoice.invoice_number}</h1>
        <div className="button-row">
          <button type="button" className="btn-secondary" onClick={handleDownloadPdf}>Download PDF</button>
          {parseFloat(invoice.balance_due) > 0 && (
            <button type="button" className="btn-primary" onClick={handlePayNow} disabled={paying}>
              {paying ? "Processing..." : "Pay Now"}
            </button>
          )}
        </div>
      </div>

      <span className={`badge badge-${invoice.status}`}>{invoice.status}</span>

      {payMessage && <div className="auth-error" style={{ marginTop: "1rem" }}>{payMessage}</div>}

      <div className="card">
        <div className="form-row">
          <div><strong>Issue Date:</strong> {invoice.issue_date}</div>
          <div><strong>Due Date:</strong> {invoice.due_date}</div>
        </div>

        <table className="data-table line-items" style={{ marginTop: "1rem" }}>
          <thead>
            <tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Amount</th></tr>
          </thead>
          <tbody>
            {invoice.lines.map((l) => (
              <tr key={l.id}>
                <td>{l.description}</td>
                <td>{l.quantity}</td>
                <td>${l.unit_price}</td>
                <td>${l.amount}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="invoice-totals">
          <div>Subtotal: ${invoice.subtotal}</div>
          <div>Tax: ${invoice.tax_total}</div>
          <div className="total-line">Total: ${invoice.total}</div>
          <div className="total-line">Balance Due: ${invoice.balance_due}</div>
        </div>

        {invoice.memo && <p className="text-muted">{invoice.memo}</p>}
      </div>

      <Link to="/portal" className="btn-link">Back to invoices</Link>
    </div>
  );
}

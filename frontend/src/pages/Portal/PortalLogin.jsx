import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePortalAuth } from "../../context/PortalAuthContext";

export default function PortalLogin() {
  const { login } = usePortalAuth();
  const navigate = useNavigate();
  const [tenant, setTenant] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(tenant.trim(), email.trim(), password);
      navigate("/portal");
    } catch (err) {
      setError(err.response?.data?.error || "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Customer Portal</h1>
        <p className="auth-subtitle">Sign in to view your invoices and orders</p>

        {error && <div className="auth-error">{error}</div>}

        <label>
          Account ID
          <input value={tenant} onChange={(e) => setTenant(e.target.value)} placeholder="demo" required autoFocus />
        </label>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>

        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function SuperAdminLogin() {
  const { superAdminLogin } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await superAdminLogin(email.trim(), password);
      navigate("/admin");
    } catch (err) {
      setError(err.response?.data?.error || "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>ETG Super-Admin</h1>
        <p className="auth-subtitle">Cross-tenant provisioning console</p>

        {error && <div className="auth-error">{error}</div>}

        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>

        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Signing in..." : "Sign in"}
        </button>

        <div className="auth-footer">
          <Link to="/login">Tenant login</Link>
        </div>
      </form>
    </div>
  );
}

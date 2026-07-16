import { Navigate } from "react-router-dom";
import { usePortalAuth } from "../context/PortalAuthContext";

export function PortalProtectedRoute({ children }) {
  const { portalUser, loading } = usePortalAuth();

  if (loading) return <div className="page-loading">Loading...</div>;
  if (!portalUser) return <Navigate to="/portal/login" replace />;

  return children;
}

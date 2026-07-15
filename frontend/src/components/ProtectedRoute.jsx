import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function ProtectedRoute({ children, requireModule, requireRole }) {
  const { user, tenant, isSuperAdmin, loading, hasModule, hasRole } = useAuth();

  if (loading) return <div className="page-loading">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (isSuperAdmin) return <Navigate to="/admin" replace />;

  if (requireModule && !hasModule(requireModule)) {
    return <div className="page-blocked">This module is not enabled for {tenant?.name}.</div>;
  }
  if (requireRole && !hasRole(...requireRole)) {
    return <div className="page-blocked">You don't have permission to view this page.</div>;
  }

  return children;
}

export function SuperAdminRoute({ children }) {
  const { isSuperAdmin, loading } = useAuth();
  if (loading) return <div className="page-loading">Loading...</div>;
  if (!isSuperAdmin) return <Navigate to="/admin/login" replace />;
  return children;
}

import { Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function SuperAdminLayout() {
  const { user, logout } = useAuth();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">ETG Super-Admin</div>
        <nav>
          <a href="/admin">Tenants</a>
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="user-name">{user?.full_name}</div>
          </div>
          <button className="btn-link" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

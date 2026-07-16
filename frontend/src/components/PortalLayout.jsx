import { NavLink, Outlet } from "react-router-dom";
import { usePortalAuth } from "../context/PortalAuthContext";

export default function PortalLayout() {
  const { customer, tenant, portalUser, logout } = usePortalAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">{tenant?.name || "Customer Portal"}</div>
        <nav>
          <div className="nav-section">
            <NavLink to="/portal" end className={({ isActive }) => (isActive ? "active" : "")}>
              Invoices
            </NavLink>
            <NavLink to="/portal/work-orders" className={({ isActive }) => (isActive ? "active" : "")}>
              Work Orders
            </NavLink>
            <NavLink to="/portal/tracking" className={({ isActive }) => (isActive ? "active" : "")}>
              Shipment Tracking
            </NavLink>
          </div>
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="user-name">{portalUser?.full_name}</div>
            <div className="user-role">{customer?.display_name}</div>
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

import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", exact: true },
  { to: "/customers", label: "Customers", module: "ar_ap" },
  { to: "/invoices", label: "Invoices", module: "ar_ap" },
  { to: "/payments", label: "Receipts", module: "ar_ap" },
  { to: "/cash-accounts", label: "Check Register", module: "ar_ap" },
  { to: "/accounts", label: "Chart of Accounts", module: "ar_ap" },
  { to: "/users", label: "Users", roles: ["owner_admin"] },
  { to: "/settings", label: "Company Settings", roles: ["owner_admin"] },
];

export default function Layout() {
  const { user, tenant, logout, hasModule, hasRole } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">{tenant?.name || "Evolve Business Suite"}</div>
        <nav>
          {NAV_ITEMS.filter((item) => {
            if (item.module && !hasModule(item.module)) return false;
            if (item.roles && !hasRole(...item.roles)) return false;
            return true;
          }).map((item) => (
            <NavLink key={item.to} to={item.to} end={item.exact} className={({ isActive }) => (isActive ? "active" : "")}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="user-name">{user?.full_name}</div>
            <div className="user-role">{user?.role?.replace(/_/g, " ")}</div>
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

import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_SECTIONS = [
  {
    items: [{ to: "/", label: "Dashboard", exact: true }],
  },
  {
    heading: "Sales",
    module: "ar_ap",
    items: [
      { to: "/customers", label: "Customers" },
      { to: "/invoices", label: "Invoices" },
      { to: "/payments", label: "Receipts" },
    ],
  },
  {
    heading: "Purchasing",
    module: "ar_ap",
    items: [
      { to: "/vendors", label: "Vendors" },
      { to: "/purchase-orders", label: "Purchase Orders" },
      { to: "/bills", label: "Bills" },
      { to: "/vendor-payments", label: "Bill Payments" },
    ],
  },
  {
    heading: "Accounting",
    module: "ar_ap",
    items: [
      { to: "/cash-accounts", label: "Check Register" },
      { to: "/accounts", label: "Chart of Accounts" },
    ],
  },
  {
    heading: "Reports",
    module: "ar_ap",
    roles: ["owner_admin", "accountant", "read_only_auditor"],
    items: [
      { to: "/reports/profit-loss", label: "Profit & Loss" },
      { to: "/reports/income", label: "Income" },
      { to: "/reports/sales-tax", label: "Sales Tax" },
      { to: "/reports/aging-receivables", label: "Aging Receivables" },
    ],
  },
  {
    heading: "Admin",
    roles: ["owner_admin"],
    items: [
      { to: "/users", label: "Users" },
      { to: "/settings", label: "Company Settings" },
      { to: "/settings/tax-rates", label: "Tax Rates" },
    ],
  },
];

export default function Layout() {
  const { user, tenant, logout, hasModule, hasRole } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">{tenant?.name || "Evolve Business Suite"}</div>
        <nav>
          {NAV_SECTIONS.filter((section) => {
            if (section.module && !hasModule(section.module)) return false;
            if (section.roles && !hasRole(...section.roles)) return false;
            return true;
          }).map((section, idx) => (
            <div className="nav-section" key={section.heading || `top-${idx}`}>
              {section.heading && <div className="nav-heading">{section.heading}</div>}
              {section.items.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.exact} className={({ isActive }) => (isActive ? "active" : "")}>
                  {item.label}
                </NavLink>
              ))}
            </div>
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

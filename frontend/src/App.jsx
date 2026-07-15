import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute, SuperAdminRoute } from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import SuperAdminLayout from "./components/SuperAdminLayout";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import CustomerList from "./pages/Customers/CustomerList";
import CustomerDetail from "./pages/Customers/CustomerDetail";
import InvoiceList from "./pages/Invoices/InvoiceList";
import InvoiceDetail from "./pages/Invoices/InvoiceDetail";
import PaymentList from "./pages/Payments/PaymentList";
import PaymentForm from "./pages/Payments/PaymentForm";
import AccountList from "./pages/Accounts/AccountList";
import CashAccountList from "./pages/CashAccounts/CashAccountList";
import Register from "./pages/CashAccounts/Register";
import CompanySettings from "./pages/Settings/CompanySettings";
import UserList from "./pages/Users/UserList";
import SuperAdminLogin from "./pages/SuperAdmin/SuperAdminLogin";
import TenantList from "./pages/SuperAdmin/TenantList";
import TenantDetail from "./pages/SuperAdmin/TenantDetail";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/admin/login" element={<SuperAdminLogin />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="customers" element={<CustomerList />} />
            <Route path="customers/:id" element={<CustomerDetail />} />
            <Route path="invoices" element={<InvoiceList />} />
            <Route path="invoices/:id" element={<InvoiceDetail />} />
            <Route path="payments" element={<PaymentList />} />
            <Route path="payments/new" element={<PaymentForm />} />
            <Route path="accounts" element={<AccountList />} />
            <Route path="cash-accounts" element={<CashAccountList />} />
            <Route path="cash-accounts/:id" element={<Register />} />
            <Route path="settings" element={<CompanySettings />} />
            <Route path="users" element={<UserList />} />
          </Route>

          <Route
            path="/admin"
            element={
              <SuperAdminRoute>
                <SuperAdminLayout />
              </SuperAdminRoute>
            }
          >
            <Route index element={<TenantList />} />
            <Route path="tenants/:id" element={<TenantDetail />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

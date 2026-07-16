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
import TaxRates from "./pages/Settings/TaxRates";
import UserList from "./pages/Users/UserList";
import VendorList from "./pages/Vendors/VendorList";
import VendorDetail from "./pages/Vendors/VendorDetail";
import BillList from "./pages/Bills/BillList";
import BillDetail from "./pages/Bills/BillDetail";
import POList from "./pages/PurchaseOrders/POList";
import PODetail from "./pages/PurchaseOrders/PODetail";
import VendorPaymentList from "./pages/VendorPayments/VendorPaymentList";
import VendorPaymentForm from "./pages/VendorPayments/VendorPaymentForm";
import ProfitLoss from "./pages/Reports/ProfitLoss";
import IncomeReport from "./pages/Reports/IncomeReport";
import SalesTax from "./pages/Reports/SalesTax";
import AgingReceivables from "./pages/Reports/AgingReceivables";
import ItemList from "./pages/Items/ItemList";
import ItemDetail from "./pages/Items/ItemDetail";
import LocationList from "./pages/Locations/LocationList";
import WorkOrderList from "./pages/WorkOrders/WorkOrderList";
import WorkOrderDetail from "./pages/WorkOrders/WorkOrderDetail";
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
            <Route path="settings/tax-rates" element={<TaxRates />} />
            <Route path="users" element={<UserList />} />
            <Route path="vendors" element={<VendorList />} />
            <Route path="vendors/:id" element={<VendorDetail />} />
            <Route path="bills" element={<BillList />} />
            <Route path="bills/:id" element={<BillDetail />} />
            <Route path="purchase-orders" element={<POList />} />
            <Route path="purchase-orders/:id" element={<PODetail />} />
            <Route path="vendor-payments" element={<VendorPaymentList />} />
            <Route path="vendor-payments/new" element={<VendorPaymentForm />} />
            <Route path="reports/profit-loss" element={<ProfitLoss />} />
            <Route path="reports/income" element={<IncomeReport />} />
            <Route path="reports/sales-tax" element={<SalesTax />} />
            <Route path="reports/aging-receivables" element={<AgingReceivables />} />
            <Route path="items" element={<ItemList />} />
            <Route path="items/:id" element={<ItemDetail />} />
            <Route path="locations" element={<LocationList />} />
            <Route path="work-orders" element={<WorkOrderList />} />
            <Route path="work-orders/:id" element={<WorkOrderDetail />} />
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

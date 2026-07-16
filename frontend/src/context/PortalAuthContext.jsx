import { createContext, useContext, useEffect, useState, useCallback } from "react";
import portalClient, { setPortalTokens, clearPortalTokens } from "../api/portalClient";

const PortalAuthContext = createContext(null);

export function PortalAuthProvider({ children }) {
  const [portalUser, setPortalUser] = useState(null);
  const [customer, setCustomer] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    const token = localStorage.getItem("portal_access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const { data } = await portalClient.get("/auth/me");
      setPortalUser(data.portal_user);
      setCustomer(data.customer);
      setTenant(data.tenant);
    } catch {
      clearPortalTokens();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const login = async (tenantSlug, email, password) => {
    const { data } = await portalClient.post("/auth/login", { tenant: tenantSlug, email, password });
    setPortalTokens(data);
    setPortalUser(data.portal_user);
    setCustomer(data.customer);
    setTenant(data.tenant);
    return data;
  };

  const logout = () => {
    clearPortalTokens();
    setPortalUser(null);
    setCustomer(null);
    setTenant(null);
  };

  return (
    <PortalAuthContext.Provider value={{ portalUser, customer, tenant, loading, login, logout }}>
      {children}
    </PortalAuthContext.Provider>
  );
}

export function usePortalAuth() {
  const ctx = useContext(PortalAuthContext);
  if (!ctx) throw new Error("usePortalAuth must be used within PortalAuthProvider");
  return ctx;
}

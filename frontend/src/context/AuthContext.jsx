import { createContext, useContext, useEffect, useState, useCallback } from "react";
import client, { setTokens, clearTokens } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const { data } = await client.get("/auth/me");
      if (data.is_super_admin) {
        setIsSuperAdmin(true);
        setUser(data.admin);
        setTenant(null);
      } else {
        setIsSuperAdmin(false);
        setUser(data.user);
        setTenant(data.tenant);
      }
    } catch {
      clearTokens();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const login = async (tenantSlug, email, password) => {
    const { data } = await client.post("/auth/login", { tenant: tenantSlug, email, password });
    setTokens(data);
    setIsSuperAdmin(false);
    setUser(data.user);
    setTenant(data.tenant);
    return data;
  };

  const superAdminLogin = async (email, password) => {
    const { data } = await client.post("/auth/superadmin/login", { email, password });
    setTokens(data);
    setIsSuperAdmin(true);
    setUser(data.admin);
    setTenant(null);
    return data;
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    setTenant(null);
    setIsSuperAdmin(false);
  };

  const hasModule = (moduleKey) => !!tenant?.modules?.[moduleKey];
  const hasRole = (...roles) => !!user && roles.includes(user.role);

  return (
    <AuthContext.Provider
      value={{ user, tenant, isSuperAdmin, loading, login, superAdminLogin, logout, hasModule, hasRole, setTenant }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000/api";

// Wholly separate axios instance + token storage from the staff app's
// client.js -- a portal session must never share state with a staff
// session in the same browser (e.g. a staff member and a customer using
// the same machine), and a portal token must never be attached to a
// staff request or vice versa.
const portalClient = axios.create({ baseURL: `${API_URL}/portal` });

function getStoredTokens() {
  return {
    access: localStorage.getItem("portal_access_token"),
    refresh: localStorage.getItem("portal_refresh_token"),
  };
}

export function setPortalTokens({ access_token, refresh_token }) {
  if (access_token) localStorage.setItem("portal_access_token", access_token);
  if (refresh_token) localStorage.setItem("portal_refresh_token", refresh_token);
}

export function clearPortalTokens() {
  localStorage.removeItem("portal_access_token");
  localStorage.removeItem("portal_refresh_token");
}

portalClient.interceptors.request.use((config) => {
  const { access } = getStoredTokens();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshPromise = null;

portalClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const { refresh } = getStoredTokens();
      if (!refresh) {
        clearPortalTokens();
        return Promise.reject(error);
      }
      try {
        if (!refreshPromise) {
          refreshPromise = axios
            .post(`${API_URL}/portal/auth/refresh`, {}, { headers: { Authorization: `Bearer ${refresh}` } })
            .finally(() => {
              refreshPromise = null;
            });
        }
        const { data } = await refreshPromise;
        setPortalTokens({ access_token: data.access_token });
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return portalClient(original);
      } catch (refreshError) {
        clearPortalTokens();
        window.location.href = "/portal/login";
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export default portalClient;

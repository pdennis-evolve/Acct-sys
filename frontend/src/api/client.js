import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000/api";

const client = axios.create({ baseURL: API_URL });

function getStoredTokens() {
  return {
    access: localStorage.getItem("access_token"),
    refresh: localStorage.getItem("refresh_token"),
  };
}

export function setTokens({ access_token, refresh_token }) {
  if (access_token) localStorage.setItem("access_token", access_token);
  if (refresh_token) localStorage.setItem("refresh_token", refresh_token);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

client.interceptors.request.use((config) => {
  const { access } = getStoredTokens();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshPromise = null;

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const { refresh } = getStoredTokens();
      if (!refresh) {
        clearTokens();
        return Promise.reject(error);
      }
      try {
        if (!refreshPromise) {
          refreshPromise = axios
            .post(`${API_URL}/auth/refresh`, {}, { headers: { Authorization: `Bearer ${refresh}` } })
            .finally(() => {
              refreshPromise = null;
            });
        }
        const { data } = await refreshPromise;
        setTokens({ access_token: data.access_token });
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return client(original);
      } catch (refreshError) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export default client;

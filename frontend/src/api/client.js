// Single axios instance for every API call.
// - withCredentials: sends the httpOnly session cookie (the token is never readable from JS).
// - Errors are normalised to { status, code, message, details } matching the backend error format.
import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  withCredentials: true,
  timeout: 30000,
});

// Fired when a request is rejected as logged-out (401) or wrong-role (403). This happens when the
// session changed in another tab (e.g. logged in as admin there), since a browser holds one session
// cookie. AuthContext listens and re-checks who is logged in, so the UI redirects instead of
// silently failing.
export const AUTH_CHANGED_EVENT = "bookleaf:auth-changed";

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status ?? 0;
    const url = err.config?.url ?? "";
    if ((status === 401 || status === 403) && !url.startsWith("/auth/")) {
      window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
    }
    const apiError = err.response?.data?.error;
    return Promise.reject({
      status,
      code: apiError?.code ?? (status ? "HTTP_ERROR" : "NETWORK_ERROR"),
      message: apiError?.message ?? "Could not reach the server. Please check your connection.",
      details: apiError?.details,
    });
  },
);

export default client;

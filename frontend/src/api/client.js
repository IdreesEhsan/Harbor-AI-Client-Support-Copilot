import axios from "axios";

/**
 * Shared HTTP client for communication with the Harbor FastAPI backend.
 *
 * Authentication tokens are automatically attached to requests when
 * the user has logged in.
 */
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Attach the JWT access token to authenticated API requests.
 */
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("harbor_access_token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

export default apiClient;
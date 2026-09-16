import { createContext, useContext, useEffect, useState } from "react";
import apiClient from "../api/client";

const AuthContext = createContext(null);

/**
 * Provides Harbor authentication state to the entire React application.
 *
 * The JWT is stored locally so a user remains authenticated after
 * refreshing the browser. The backend remains responsible for validating
 * the token and determining the user's role.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  /**
   * Restore the authenticated user when the application starts.
   */
  useEffect(() => {
    const restoreSession = async () => {
      const token = localStorage.getItem("harbor_access_token");

      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const response = await apiClient.get("/auth/me");
        setUser(response.data);
      } catch (error) {
        console.error("Unable to restore Harbor session:", error);
        localStorage.removeItem("harbor_access_token");
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, []);

  /**
   * Authenticate a user against the FastAPI login endpoint.
   */
  const login = async (email, password) => {
    const response = await apiClient.post("/auth/login", {
      email,
      password,
    });

    const token = response.data.access_token;

    localStorage.setItem("harbor_access_token", token);

    // apiClient automatically attaches the newly stored JWT.
    const userResponse = await apiClient.get("/auth/me");

    setUser(userResponse.data);

    return userResponse.data;
  };

  const logout = () => {
    localStorage.removeItem("harbor_access_token");
    setUser(null);
  };

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: Boolean(user),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Convenience hook for accessing Harbor authentication.
 */
export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
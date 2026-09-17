import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import apiClient from "../api/client";


const AuthContext =
  createContext(null);


export function AuthProvider({
  children,
}) {
  const [
    user,
    setUser,
  ] = useState(null);

  const [
    loading,
    setLoading,
  ] = useState(true);


  useEffect(() => {
    const restoreSession =
      async () => {
        const token =
          localStorage.getItem(
            "harbor_access_token"
          );

        if (!token) {
          setLoading(false);
          return;
        }

        try {
          const response =
            await apiClient.get(
              "/auth/me"
            );

          setUser(
            response.data
          );

        } catch (error) {
          console.error(
            "Unable to restore Harbor session:",
            error
          );

          localStorage.removeItem(
            "harbor_access_token"
          );

          setUser(null);

        } finally {
          setLoading(false);
        }
      };

    restoreSession();
  }, []);


  const login = async (
    email,
    password
  ) => {
    const response =
      await apiClient.post(
        "/auth/login",
        {
          email:
            email
              .trim()
              .toLowerCase(),

          password,
        }
      );

    const token =
      response.data.access_token;

    localStorage.setItem(
      "harbor_access_token",
      token
    );

    const userResponse =
      await apiClient.get(
        "/auth/me"
      );

    setUser(
      userResponse.data
    );

    return (
      userResponse.data
    );
  };


  const logout = () => {
    localStorage.removeItem(
      "harbor_access_token"
    );

    setUser(null);
  };


  const value = {
    user,
    loading,
    login,
    logout,

    isAuthenticated:
      Boolean(user),

    isStaff:
      user?.role
        === "support_agent"
      || user?.role
        === "admin",

    isCustomer:
      user?.role
        === "customer",
  };


  return (
    <AuthContext.Provider
      value={value}
    >
      {children}
    </AuthContext.Provider>
  );
}


export function useAuth() {
  const context =
    useContext(
      AuthContext
    );

  if (!context) {
    throw new Error(
      "useAuth must be used "
      + "inside AuthProvider"
    );
  }

  return context;
}
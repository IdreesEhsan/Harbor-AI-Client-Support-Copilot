import {
  Navigate,
} from "react-router-dom";

import {
  useAuth,
} from "../context/AuthContext";


export default function ProtectedRoute({
  children,
}) {
  const {
    user,
    isAuthenticated,
    loading,
  } = useAuth();


  if (loading) {
    return (
      <div className="fullscreen-loader">

        <div className="loader-logo">
          H
        </div>

        <div className="loader-spinner" />

        <p>
          Restoring your session...
        </p>

      </div>
    );
  }


  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }


  const isStaff =
    user?.role
      === "support_agent"
    || user?.role
      === "admin";


  if (isStaff) {
    return (
      <Navigate
        to="/staff"
        replace
      />
    );
  }


  if (
    user?.role
    !== "customer"
  ) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }


  return children;
}
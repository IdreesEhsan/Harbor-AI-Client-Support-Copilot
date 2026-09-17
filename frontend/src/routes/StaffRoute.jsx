import {
  Navigate,
} from "react-router-dom";

import {
  useAuth,
} from "../context/AuthContext";


export default function StaffRoute({
  children,
}) {
  const {
    user,
    loading,
    isAuthenticated,
  } = useAuth();


  if (loading) {
    return (
      <div className="fullscreen-loader">

        <div className="loader-logo">
          H
        </div>

        <div className="loader-spinner" />

        <p>
          Loading Harbor operations...
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


  if (!isStaff) {
    return (
      <Navigate
        to="/chat"
        replace
      />
    );
  }


  return children;
}
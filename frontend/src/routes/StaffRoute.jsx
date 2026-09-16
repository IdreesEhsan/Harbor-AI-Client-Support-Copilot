import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * Restricts staff functionality to Harbor support agents
 * and administrators.
 */
export default function StaffRoute({ children }) {
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return <p>Loading Harbor...</p>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const isStaff =
    user?.role === "support_agent" ||
    user?.role === "admin";

  if (!isStaff) {
    return <Navigate to="/chat" replace />;
  }

  return children;
}   
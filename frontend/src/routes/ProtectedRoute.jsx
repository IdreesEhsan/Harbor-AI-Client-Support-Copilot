import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * Prevents unauthenticated visitors from accessing protected Harbor pages.
 */
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <p>Loading Harbor...</p>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
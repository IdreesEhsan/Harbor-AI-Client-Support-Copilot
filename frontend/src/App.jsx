import { Navigate, Route, Routes } from "react-router-dom";

import LoginPage from "./pages/LoginPage";
import ChatPage from "./pages/ChatPage";
import StaffPage from "./pages/StaffPage";

import ProtectedRoute from "./routes/ProtectedRoute";
import StaffRoute from "./routes/StaffRoute";

import { useAuth } from "./context/AuthContext";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <p>Loading Harbor...</p>;
  }

  /**
   * Decide the default landing page based on the authenticated
   * user's role.
   *
   * Customers go to the AI support chat.
   * Support agents and administrators go to the staff console.
   */
  const homePath =
    user?.role === "support_agent" || user?.role === "admin"
      ? "/staff"
      : "/chat";

  return (
    <Routes>
      {/* Public route */}
      <Route path="/login" element={<LoginPage />} />

      {/* Authenticated customer/support chat */}
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />

      {/* Staff-only ticket management console */}
      <Route
        path="/staff"
        element={
          <StaffRoute>
            <StaffPage />
          </StaffRoute>
        }
      />

      {/* Role-aware home redirect */}
      <Route
        path="/"
        element={
          user ? (
            <Navigate to={homePath} replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      {/* Unknown routes return to the appropriate home page */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
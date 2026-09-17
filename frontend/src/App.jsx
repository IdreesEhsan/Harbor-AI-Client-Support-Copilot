import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import ChatPage from "./pages/ChatPage";
import StaffPage from "./pages/StaffPage";

import ProtectedRoute from "./routes/ProtectedRoute";
import StaffRoute from "./routes/StaffRoute";

import {
  useAuth,
} from "./context/AuthContext";


function HarborLoader() {
  return (
    <div className="fullscreen-loader">

      <div className="loader-logo">
        H
      </div>

      <div className="loader-spinner" />

      <p>
        Loading Harbor...
      </p>

    </div>
  );
}


export default function App() {
  const {
    user,
    loading,
  } = useAuth();


  if (loading) {
    return (
      <HarborLoader />
    );
  }


  const isStaff =
    user?.role
      === "support_agent"
    || user?.role
      === "admin";


  const homePath =
    isStaff
      ? "/staff"
      : "/chat";


  return (
    <Routes>

      <Route
        path="/login"
        element={
          <LoginPage />
        }
      />


      <Route
        path="/register"
        element={
          <RegisterPage />
        }
      />


      <Route
        path="/verify-email"
        element={
          <VerifyEmailPage />
        }
      />


      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />


      <Route
        path="/staff"
        element={
          <StaffRoute>
            <StaffPage />
          </StaffRoute>
        }
      />


      <Route
        path="/"
        element={
          user
            ? (
              <Navigate
                to={homePath}
                replace
              />
            )
            : (
              <Navigate
                to="/login"
                replace
              />
            )
        }
      />


      <Route
        path="*"
        element={
          <Navigate
            to="/"
            replace
          />
        }
      />

    </Routes>
  );
}
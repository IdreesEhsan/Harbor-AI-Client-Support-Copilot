import {
  useState,
} from "react";

import {
  Link,
  Navigate,
  useNavigate,
} from "react-router-dom";

import {
  useAuth,
} from "../context/AuthContext";


export default function LoginPage() {
  const {
    login,
    isAuthenticated,
    user,
  } = useAuth();

  const navigate =
    useNavigate();

  const [
    email,
    setEmail,
  ] = useState("");

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    submitting,
    setSubmitting,
  ] = useState(false);


  if (isAuthenticated) {
    const isStaff =
      user?.role
        === "support_agent"
      || user?.role
        === "admin";

    return (
      <Navigate
        to={
          isStaff
            ? "/staff"
            : "/chat"
        }
        replace
      />
    );
  }


  const handleSubmit = async (
    event
  ) => {
    event.preventDefault();

    setError("");
    setSubmitting(true);

    try {
      const authenticatedUser =
        await login(
          email,
          password
        );

      const isStaff =
        authenticatedUser.role
          === "support_agent"
        || authenticatedUser.role
          === "admin";

      navigate(
        isStaff
          ? "/staff"
          : "/chat",
        {
          replace: true,
        }
      );

    } catch (err) {
      const message =
        err.response?.data?.detail
        || (
          "Unable to sign in. "
          + "Please check your credentials."
        );

      setError(
        message
      );

    } finally {
      setSubmitting(false);
    }
  };


  return (
    <div className="auth-page login-auth-page">

      <div className="background-orb background-orb-one" />
      <div className="background-orb background-orb-two" />
      <div className="background-grid" />


      <div className="auth-shell login-auth-shell">

        <section className="auth-brand-panel login-brand-panel">

          <div className="brand-mark">

            <div className="brand-icon">
              H
            </div>

            <div>
              <span className="brand-name">
                Harbor
              </span>

              <span className="brand-caption">
                AI Client Support Copilot
              </span>
            </div>

          </div>


          <div className="auth-hero-copy login-hero-copy">

            <span className="eyebrow">
              INTELLIGENT CUSTOMER OPERATIONS
            </span>

            <h1>
              Support that knows when
              to answer and when to
              escalate.
            </h1>

            <p>
              Harbor combines grounded AI,
              persistent memory, human approval,
              and business automation in one
              secure support workflow.
            </p>

          </div>


          <div className="feature-stack login-feature-stack">

            <div className="feature-row">

              <div className="feature-icon">
                ✓
              </div>

              <div>
                <strong>
                  Grounded AI answers
                </strong>

                <span>
                  RAG-powered responses
                  with citations.
                </span>
              </div>

            </div>


            <div className="feature-row">

              <div className="feature-icon">
                ✓
              </div>

              <div>
                <strong>
                  Human-in-the-loop safety
                </strong>

                <span>
                  External actions require
                  staff approval.
                </span>
              </div>

            </div>


            <div className="feature-row">

              <div className="feature-icon">
                ✓
              </div>

              <div>
                <strong>
                  Connected operations
                </strong>

                <span>
                  Monday.com, n8n,
                  Supabase and Snowflake.
                </span>
              </div>

            </div>

          </div>


          <div className="auth-trust-row login-trust-row">

            <span className="status-dot" />

            Secure AI support workspace

          </div>

        </section>


        <section className="auth-form-panel">

          <div className="glass-card login-card compact-login-card">

            <div className="login-card-header">

              <span className="mini-badge">
                SECURE ACCESS
              </span>

              <h2>
                Welcome back
              </h2>

              <p>
                Sign in to continue to your
                Harbor workspace.
              </p>

            </div>


            <form
              className="auth-form"
              onSubmit={handleSubmit}
            >

              <div className="form-group">

                <label htmlFor="email">
                  Email address
                </label>

                <div className="input-shell">

                  <span className="input-icon">
                    @
                  </span>

                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(event) =>
                      setEmail(
                        event.target.value
                      )
                    }
                    placeholder="you@company.com"
                    autoComplete="email"
                    required
                  />

                </div>

              </div>


              <div className="form-group">

                <label htmlFor="password">
                  Password
                </label>

                <div className="input-shell">

                  <span className="input-icon">
                    ●
                  </span>

                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(event) =>
                      setPassword(
                        event.target.value
                      )
                    }
                    placeholder="Enter your password"
                    autoComplete="current-password"
                    required
                  />

                </div>

              </div>


              {error && (
                <div className="alert alert-error">

                  <div>
                    <strong>
                      Sign in failed
                    </strong>

                    <span>
                      {error}
                    </span>
                  </div>

                </div>
              )}


              <button
                className="primary-button auth-submit"
                type="submit"
                disabled={submitting}
              >
                {submitting
                  ? (
                    <>
                      <span className="button-spinner" />

                      Signing in...
                    </>
                  )
                  : (
                    <>
                      Sign in to Harbor

                      <span>
                        →
                      </span>
                    </>
                  )}
              </button>

            </form>


            <div className="login-card-footer">

              <div className="secure-indicator">

                <span className="status-dot" />

                Protected by Harbor authentication

              </div>


              <p className="auth-switch-text">

                Don't have an account?{" "}

                <Link
                  to="/register"
                  className="auth-link"
                >
                  Create account
                </Link>

              </p>

            </div>

          </div>

        </section>

      </div>

    </div>
  );
}
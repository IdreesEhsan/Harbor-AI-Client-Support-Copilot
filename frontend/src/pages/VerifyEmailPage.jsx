import {
  useState,
} from "react";

import {
  Link,
  Navigate,
  useNavigate,
} from "react-router-dom";

import apiClient from "../api/client";

import {
  useAuth,
} from "../context/AuthContext";


export default function RegisterPage() {
  const {
    isAuthenticated,
  } = useAuth();

  const navigate =
    useNavigate();

  const [
    fullName,
    setFullName,
  ] = useState("");

  const [
    age,
    setAge,
  ] = useState("");

  const [
    country,
    setCountry,
  ] = useState("");

  const [
    email,
    setEmail,
  ] = useState("");

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    confirmPassword,
    setConfirmPassword,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    submitting,
    setSubmitting,
  ] = useState(false);

  const [
    verificationSent,
    setVerificationSent,
  ] = useState(false);

  const [
    registeredEmail,
    setRegisteredEmail,
  ] = useState("");


  if (isAuthenticated) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }


  const validatePassword = (
    value
  ) => {
    if (value.length < 8) {
      return (
        "Password must be at least "
        + "8 characters long."
      );
    }

    if (
      !/[A-Za-z]/.test(
        value
      )
    ) {
      return (
        "Password must contain at least "
        + "one letter."
      );
    }

    if (
      !/\d/.test(
        value
      )
    ) {
      return (
        "Password must contain at least "
        + "one number."
      );
    }

    if (
      !/[!@#$%^&*(),.?":{}|<>]/.test(
        value
      )
    ) {
      return (
        "Password must contain at least "
        + "one special character."
      );
    }

    return null;
  };


  const validateForm = () => {
    if (!fullName.trim()) {
      return (
        "Please enter your full name."
      );
    }

    const numericAge =
      Number(age);

    if (
      !Number.isInteger(
        numericAge
      )
      || numericAge <= 0
      || numericAge > 120
    ) {
      return (
        "Please enter a valid age."
      );
    }

    if (!country.trim()) {
      return (
        "Please enter your country."
      );
    }

    if (!email.trim()) {
      return (
        "Please enter your email address."
      );
    }

    const passwordError =
      validatePassword(
        password
      );

    if (passwordError) {
      return passwordError;
    }

    if (
      password
      !== confirmPassword
    ) {
      return (
        "Passwords do not match."
      );
    }

    return null;
  };


  const handleSubmit = async (
    event
  ) => {
    event.preventDefault();

    setError("");

    const validationError =
      validateForm();

    if (validationError) {
      setError(
        validationError
      );

      return;
    }

    setSubmitting(true);

    try {
      const response =
        await apiClient.post(
          "/auth/register",
          {
            full_name:
              fullName.trim(),

            age:
              Number(age),

            country:
              country.trim(),

            email:
              email
                .trim()
                .toLowerCase(),

            password,
          }
        );

      setRegisteredEmail(
        response.data.email
        || email
          .trim()
          .toLowerCase()
      );

      setVerificationSent(
        true
      );

    } catch (err) {
      console.error(
        "Harbor registration failed:",
        err
      );

      const detail =
        err.response?.data?.detail;

      if (
        Array.isArray(detail)
      ) {
        setError(
          detail
            .map(
              (item) =>
                item.msg
            )
            .join(" ")
        );

      } else {
        setError(
          detail
          || (
            "Unable to create your "
            + "account. Please try again."
          )
        );
      }

    } finally {
      setSubmitting(false);
    }
  };


  if (verificationSent) {
    return (
      <div className="auth-page">

        <div className="background-orb background-orb-one" />
        <div className="background-orb background-orb-two" />
        <div className="background-grid" />


        <div className="verification-shell">

          <div className="glass-card verification-card">

            <div className="verification-icon verification-icon-success">
              ✉
            </div>

            <span className="mini-badge">
              VERIFICATION SENT
            </span>

            <h1>
              Check your email
            </h1>

            <p>
              We've sent a verification
              link to:
            </p>

            <strong className="verification-email">
              {registeredEmail}
            </strong>

            <p className="verification-description">
              Open the email and click the
              verification link to activate
              your Harbor account. You cannot
              sign in until your email has
              been verified.
            </p>


            <button
              type="button"
              className="primary-button verification-button"
              onClick={() =>
                navigate(
                  "/login"
                )
              }
            >
              Go to Login

              <span>
                →
              </span>
            </button>


            <p className="verification-help">
              Didn't receive the email?
              Check your spam or junk folder.
            </p>

          </div>

        </div>

      </div>
    );
  }


  return (
    <div className="auth-page">

      <div className="background-orb background-orb-one" />
      <div className="background-orb background-orb-two" />
      <div className="background-grid" />


      <div className="auth-shell">

        <section className="auth-brand-panel">

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


          <div className="auth-hero-copy register-hero-copy">

            <span className="eyebrow">
              INTELLIGENT CUSTOMER OPERATIONS
            </span>

            <h1>
              Your smarter support
              experience starts here.
            </h1>

            <p>
              Create a verified Harbor customer
              account to access grounded AI
              support and human escalation.
            </p>

          </div>


          <div className="feature-stack">

            <div className="feature-row">

              <div className="feature-icon">
                ✓
              </div>

              <div>
                <strong>
                  Grounded answers
                </strong>

                <span>
                  Knowledge-base responses
                  backed by citations.
                </span>
              </div>

            </div>


            <div className="feature-row">

              <div className="feature-icon">
                ✓
              </div>

              <div>
                <strong>
                  Conversation memory
                </strong>

                <span>
                  Harbor retains useful
                  conversation context.
                </span>
              </div>

            </div>


            <div className="feature-row">

              <div className="feature-icon">
                ✓
              </div>

              <div>
                <strong>
                  Verified accounts
                </strong>

                <span>
                  Email verification protects
                  access to Harbor.
                </span>
              </div>

            </div>

          </div>


          <div className="auth-trust-row">

            <span className="status-dot" />

            Secure customer registration

          </div>

        </section>


        <section className="auth-form-panel">

          <div className="glass-card login-card register-card">

            <div className="login-card-header">

              <span className="mini-badge">
                CUSTOMER SIGN UP
              </span>

              <h2>
                Join Harbor
              </h2>

              <p>
                Public registration creates
                a customer account.
              </p>

            </div>


            <form
              className="auth-form register-form"
              onSubmit={handleSubmit}
            >

              <div className="form-group">

                <label htmlFor="fullName">
                  Full name
                </label>

                <div className="input-shell">

                  <span className="input-icon">
                    ◯
                  </span>

                  <input
                    id="fullName"
                    type="text"
                    value={fullName}
                    onChange={(event) =>
                      setFullName(
                        event.target.value
                      )
                    }
                    placeholder="Your full name"
                    autoComplete="name"
                    required
                  />

                </div>

              </div>


              <div className="register-grid">

                <div className="form-group">

                  <label htmlFor="age">
                    Age
                  </label>

                  <div className="input-shell">

                    <span className="input-icon">
                      #
                    </span>

                    <input
                      id="age"
                      type="number"
                      min="1"
                      max="120"
                      value={age}
                      onChange={(event) =>
                        setAge(
                          event.target.value
                        )
                      }
                      placeholder="Age"
                      required
                    />

                  </div>

                </div>


                <div className="form-group">

                  <label htmlFor="country">
                    Country
                  </label>

                  <div className="input-shell">

                    <span className="input-icon">
                      ◇
                    </span>

                    <input
                      id="country"
                      type="text"
                      value={country}
                      onChange={(event) =>
                        setCountry(
                          event.target.value
                        )
                      }
                      placeholder="Country"
                      autoComplete="country-name"
                      required
                    />

                  </div>

                </div>

              </div>


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
                    placeholder="you@example.com"
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
                    placeholder="Create a password"
                    autoComplete="new-password"
                    required
                  />

                </div>

                <span className="form-hint">
                  8+ characters with a letter,
                  number and special character.
                </span>

              </div>


              <div className="form-group">

                <label htmlFor="confirmPassword">
                  Confirm password
                </label>

                <div className="input-shell">

                  <span className="input-icon">
                    ●
                  </span>

                  <input
                    id="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(event) =>
                      setConfirmPassword(
                        event.target.value
                      )
                    }
                    placeholder="Repeat your password"
                    autoComplete="new-password"
                    required
                  />

                </div>

              </div>


              {error && (
                <div className="alert alert-error">

                  <div>
                    <strong>
                      Registration failed
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
                      Creating account...
                    </>
                  )
                  : (
                    <>
                      Create customer account

                      <span>
                        →
                      </span>
                    </>
                  )}
              </button>

            </form>


            <div className="login-card-footer">

              <p className="auth-switch-text">

                Already have an account?{" "}

                <Link
                  to="/login"
                  className="auth-link"
                >
                  Sign in
                </Link>

              </p>

            </div>

          </div>

        </section>

      </div>

    </div>
  );
}
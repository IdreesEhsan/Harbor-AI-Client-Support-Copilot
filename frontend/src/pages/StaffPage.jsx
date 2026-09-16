import { useCallback, useEffect, useState } from "react";

import {
  executeTicket,
  getTickets,
  reviewTicket,
} from "../api/tickets";

import { useAuth } from "../context/AuthContext";

/**
 * Harbor staff console.
 *
 * Support agents and administrators can:
 * - review support tickets;
 * - approve or reject pending tickets;
 * - execute approved tickets through Harbor's controlled backend workflow.
 *
 * All security-sensitive decisions remain enforced by FastAPI.
 */
export default function StaffPage() {
  const { user, logout } = useAuth();

  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [processingTicketId, setProcessingTicketId] = useState(null);

  /**
   * Load tickets from the Harbor backend.
   */
  const loadTickets = useCallback(async (showRefreshState = false) => {
    setError("");

    if (showRefreshState) {
      setRefreshing(true);
    }

    try {
      const data = await getTickets();

      setTickets(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Unable to load Harbor tickets:", err);

      setError(
        err.response?.data?.detail ||
          "Unable to load support tickets."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  /**
   * Load tickets when the staff console opens.
   */
  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  /**
   * Approve or reject a pending ticket.
   */
  const handleReview = async (ticketId, approved) => {
    setProcessingTicketId(ticketId);
    setError("");
    setSuccessMessage("");

    try {
      await reviewTicket(ticketId, approved);

      setSuccessMessage(
        approved
          ? "Ticket approved successfully."
          : "Ticket rejected successfully."
      );

      await loadTickets();
    } catch (err) {
      console.error("Unable to review ticket:", err);

      setError(
        err.response?.data?.detail ||
          "Unable to review the support ticket."
      );
    } finally {
      setProcessingTicketId(null);
    }
  };

  /**
   * Execute a ticket after human approval.
   *
   * The backend performs the real security checks, execution claim,
   * idempotency lookup, Monday.com operation, and persistence.
   */
  const handleExecute = async (ticketId) => {
    setProcessingTicketId(ticketId);
    setError("");
    setSuccessMessage("");

    try {
      await executeTicket(ticketId);

      setSuccessMessage(
        "Ticket executed successfully."
      );

      await loadTickets();
    } catch (err) {
      console.error("Unable to execute ticket:", err);

      setError(
        err.response?.data?.detail ||
          "Unable to execute the support ticket."
      );
    } finally {
      setProcessingTicketId(null);
    }
  };

  /**
   * Convert backend enum-style values into readable UI labels.
   *
   * Example:
   * pending_approval -> Pending Approval
   */
  const formatLabel = (value) => {
    if (!value) {
      return "Unknown";
    }

    return String(value)
      .replaceAll("_", " ")
      .replace(/\b\w/g, (character) =>
        character.toUpperCase()
      );
  };

  if (loading) {
    return (
      <main>
        <h1>Harbor Staff Console</h1>
        <p>Loading support tickets...</p>
      </main>
    );
  }

  return (
    <main>
      <header>
        <h1>Harbor Staff Console</h1>

        <p>
          Review, approve, and execute escalated customer
          support tickets.
        </p>

        <p>
          Signed in as{" "}
          <strong>{user?.email}</strong>
          {" · "}
          Role: <strong>{user?.role}</strong>
        </p>

        <button
          type="button"
          onClick={() => loadTickets(true)}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing..." : "Refresh Tickets"}
        </button>

        {" "}

        <button
          type="button"
          onClick={logout}
        >
          Logout
        </button>
      </header>

      <hr />

      {error && (
        <section>
          <p>
            <strong>Error:</strong> {error}
          </p>
        </section>
      )}

      {successMessage && (
        <section>
          <p>
            <strong>{successMessage}</strong>
          </p>
        </section>
      )}

      <section>
        <h2>Support Tickets</h2>

        {tickets.length === 0 ? (
          <p>No support tickets are currently available.</p>
        ) : (
          tickets.map((ticket) => {
            const isProcessing =
              processingTicketId === ticket.id;

            const pendingApproval =
              ticket.approval_status === "pending";

            const approved =
              ticket.approval_status === "approved";

            const canExecute =
              approved &&
              (
                ticket.status === "approved" ||
                ticket.status === "executing"
              ) &&
              !ticket.monday_item_id;

            return (
              <article
                key={ticket.id}
                style={{
                  border: "1px solid #ccc",
                  padding: "16px",
                  marginBottom: "16px",
                  borderRadius: "8px",
                }}
              >
                <h3>
                  {ticket.title || "Support Ticket"}
                </h3>

                <p>
                  <strong>Ticket ID:</strong>{" "}
                  {ticket.id}
                </p>

                {ticket.description && (
                  <p>
                    <strong>Description:</strong>{" "}
                    {ticket.description}
                  </p>
                )}

                <p>
                  <strong>Severity:</strong>{" "}
                  {formatLabel(ticket.severity)}
                </p>

                <p>
                  <strong>Status:</strong>{" "}
                  {formatLabel(ticket.status)}
                </p>

                <p>
                  <strong>Approval:</strong>{" "}
                  {formatLabel(ticket.approval_status)}
                </p>

                {ticket.monday_item_id && (
                  <p>
                    <strong>Monday Item ID:</strong>{" "}
                    {ticket.monday_item_id}
                  </p>
                )}

                {ticket.external_status && (
                  <p>
                    <strong>External Status:</strong>{" "}
                    {ticket.external_status}
                  </p>
                )}

                {ticket.failure_reason && (
                  <p>
                    <strong>Execution Failure:</strong>{" "}
                    {ticket.failure_reason}
                  </p>
                )}

                {pendingApproval && (
                  <div>
                    <button
                      type="button"
                      disabled={isProcessing}
                      onClick={() =>
                        handleReview(ticket.id, true)
                      }
                    >
                      {isProcessing
                        ? "Processing..."
                        : "Approve"}
                    </button>

                    {" "}

                    <button
                      type="button"
                      disabled={isProcessing}
                      onClick={() =>
                        handleReview(ticket.id, false)
                      }
                    >
                      {isProcessing
                        ? "Processing..."
                        : "Reject"}
                    </button>
                  </div>
                )}

                {canExecute && (
                  <div>
                    <button
                      type="button"
                      disabled={isProcessing}
                      onClick={() =>
                        handleExecute(ticket.id)
                      }
                    >
                      {isProcessing
                        ? "Executing..."
                        : "Execute Ticket"}
                    </button>
                  </div>
                )}

                {ticket.monday_item_id && (
                  <p>
                    <strong>
                      Ticket executed and synchronized with
                      Monday.com.
                    </strong>
                  </p>
                )}
              </article>
            );
          })
        )}
      </section>
    </main>
  );
}
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  executeTicket,
  getTickets,
  reviewTicket,
} from "../api/tickets";

import {
  useAuth,
} from "../context/AuthContext";


export default function StaffPage() {
  const {
    user,
    logout,
  } = useAuth();

  const [
    tickets,
    setTickets,
  ] = useState([]);

  const [
    activeTab,
    setActiveTab,
  ] = useState("pending");

  const [
    searchQuery,
    setSearchQuery,
  ] = useState("");

  const [
    severityFilter,
    setSeverityFilter,
  ] = useState("all");

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    successMessage,
    setSuccessMessage,
  ] = useState("");

  const [
    processingTicketId,
    setProcessingTicketId,
  ] = useState(null);


  /* =======================================================
     LOAD TICKETS
     ======================================================= */

  const loadTickets =
    useCallback(
      async (
        showRefreshState = false
      ) => {
        setError("");

        if (showRefreshState) {
          setRefreshing(true);
        }

        try {
          const data =
            await getTickets();

          setTickets(
            Array.isArray(data)
              ? data
              : []
          );

        } catch (err) {
          console.error(
            "Unable to load Harbor tickets:",
            err
          );

          setError(
            err.response?.data?.detail
            || "Unable to load support tickets."
          );

        } finally {
          setLoading(false);
          setRefreshing(false);
        }
      },
      []
    );


  useEffect(() => {
    loadTickets();
  }, [loadTickets]);


  /* =======================================================
     APPROVE / REJECT
     ======================================================= */

  const handleReview =
    async (
      ticketId,
      approved
    ) => {
      setProcessingTicketId(
        ticketId
      );

      setError("");
      setSuccessMessage("");

      try {
        await reviewTicket(
          ticketId,
          approved
        );

        setSuccessMessage(
          approved
            ? "Ticket approved successfully."
            : "Ticket rejected successfully."
        );

        await loadTickets();

        setActiveTab(
          approved
            ? "approved"
            : "rejected"
        );

      } catch (err) {
        console.error(
          "Unable to review ticket:",
          err
        );

        setError(
          err.response?.data?.detail
          || "Unable to review the support ticket."
        );

      } finally {
        setProcessingTicketId(
          null
        );
      }
    };


  /* =======================================================
     EXECUTE
     ======================================================= */

  const handleExecute =
    async (
      ticketId
    ) => {
      setProcessingTicketId(
        ticketId
      );

      setError("");
      setSuccessMessage("");

      try {
        await executeTicket(
          ticketId
        );

        setSuccessMessage(
          "Ticket executed and synchronized successfully."
        );

        await loadTickets();

        setActiveTab(
          "successful"
        );

      } catch (err) {
        console.error(
          "Unable to execute ticket:",
          err
        );

        setError(
          err.response?.data?.detail
          || "Unable to execute the support ticket."
        );

      } finally {
        setProcessingTicketId(
          null
        );
      }
    };


  /* =======================================================
     HELPERS
     ======================================================= */

  const formatLabel = (
    value
  ) => {
    if (!value) {
      return "Unknown";
    }

    return String(value)
      .replaceAll(
        "_",
        " "
      )
      .replace(
        /\b\w/g,
        (character) =>
          character.toUpperCase()
      );
  };


  const getSeverityClass = (
    severity
  ) => {
    const value =
      String(
        severity || ""
      ).toLowerCase();

    if (
      value === "critical"
    ) {
      return "badge badge-danger";
    }

    if (
      value === "high"
      || value === "medium"
    ) {
      return "badge badge-warning";
    }

    return "badge badge-success";
  };


  const getStatusClass = (
    status
  ) => {
    if (
      status === "open"
      || status === "in_progress"
      || status === "resolved"
      || status === "closed"
    ) {
      return "badge badge-success";
    }

    if (
      status === "rejected"
      || status === "failed"
    ) {
      return "badge badge-danger";
    }

    return "badge badge-warning";
  };


  /* =======================================================
     RAW WORKFLOW GROUPS
     ======================================================= */

  const groups =
    useMemo(
      () => ({
        pending:
          tickets.filter(
            (ticket) =>
              ticket.status
              === "pending_approval"
          ),

        approved:
          tickets.filter(
            (ticket) =>
              ticket.status === "approved"
              || ticket.status === "executing"
          ),

        successful:
          tickets.filter(
            (ticket) =>
              ticket.status === "open"
              || ticket.status === "in_progress"
              || ticket.status === "resolved"
              || ticket.status === "closed"
          ),

        rejected:
          tickets.filter(
            (ticket) =>
              ticket.status === "rejected"
              || ticket.status === "failed"
          ),
      }),
      [tickets]
    );


  /* =======================================================
     FILTER ACTIVE TAB
     ======================================================= */

  const filteredActiveGroup =
    useMemo(
      () => {
        const query =
          searchQuery
            .trim()
            .toLowerCase();

        const currentGroup =
          groups[
            activeTab
          ] || [];

        return currentGroup.filter(
          (ticket) => {
            const customerName =
              ticket.customer?.full_name
              || "";

            const customerEmail =
              ticket.customer?.email
              || "";

            const searchableText = [
              ticket.id,
              ticket.title,
              ticket.description,
              customerName,
              customerEmail,
            ]
              .filter(Boolean)
              .join(" ")
              .toLowerCase();

            const matchesSearch =
              !query
              || searchableText.includes(
                query
              );

            const matchesSeverity =
              severityFilter === "all"
              || ticket.severity
              === severityFilter;

            return (
              matchesSearch
              && matchesSeverity
            );
          }
        );
      },
      [
        activeTab,
        groups,
        searchQuery,
        severityFilter,
      ]
    );


  const statistics =
    useMemo(
      () => ({
        total:
          tickets.length,

        pending:
          groups.pending.length,

        approved:
          groups.approved.length,

        successful:
          groups.successful.length,
      }),
      [
        tickets,
        groups,
      ]
    );


  const tabConfig = {
    pending: {
      title:
        "Pending Review",

      description:
        "New customer escalations waiting for a human decision.",
    },

    approved: {
      title:
        "Approved / Ready to Execute",

      description:
        "Tickets approved by staff and ready for controlled execution.",
    },

    successful: {
      title:
        "Successful / Processed",

      description:
        "Tickets successfully executed or progressing through support.",
    },

    rejected: {
      title:
        "Rejected / Failed",

      description:
        "Tickets rejected by staff or unable to complete successfully.",
    },
  };


  const clearFilters = () => {
    setSearchQuery("");
    setSeverityFilter("all");
  };


  /* =======================================================
     TICKET CARD
     ======================================================= */

  const renderTicketCard = (
    ticket
  ) => {
    const isProcessing =
      processingTicketId
      === ticket.id;

    const pendingApproval =
      ticket.approval_status
      === "pending";

    const canExecute =
      ticket.approval_status
      === "approved"
      && (
        ticket.status
        === "approved"
        || ticket.status
        === "executing"
      )
      && !ticket.monday_item_id;

    const customer =
      ticket.customer;

    const customerName =
      customer?.full_name
      || "Unknown customer";

    const customerInitial =
      customerName
        .charAt(0)
        .toUpperCase();


    return (
      <article
        key={ticket.id}
        className="ticket-card"
      >

        <div className="ticket-card-top">

          <div className="ticket-main-info">

            <div className="ticket-title-row">

              <h3>
                {ticket.title
                  || "Support Ticket"}
              </h3>

              <span
                className={
                  getSeverityClass(
                    ticket.severity
                  )
                }
              >
                {formatLabel(
                  ticket.severity
                )}
              </span>

            </div>

            <span className="ticket-number">
              Ticket{" "}
              {String(
                ticket.id
              ).slice(
                0,
                8
              )}
            </span>

          </div>


          <span
            className={
              getStatusClass(
                ticket.status
              )
            }
          >
            {formatLabel(
              ticket.status
            )}
          </span>

        </div>


        <div className="ticket-customer-panel">

          <div className="ticket-customer-avatar">
            {customerInitial}
          </div>


          <div className="ticket-customer-content">

            <span className="ticket-customer-label">
              Customer
            </span>

            <strong className="ticket-customer-name">
              {customerName}
            </strong>

            {customer?.email && (
              <span className="ticket-customer-email">
                {customer.email}
              </span>
            )}

          </div>


          <div className="ticket-customer-details">

            <div>

              <span>
                Country
              </span>

              <strong>
                {customer?.country
                  || "Not provided"}
              </strong>

            </div>


            <div>

              <span>
                Age
              </span>

              <strong>
                {customer?.age
                  ?? "Not provided"}
              </strong>

            </div>

          </div>

        </div>


        {ticket.description && (
          <div className="ticket-request">

            <span className="ticket-request-label">
              Customer request
            </span>

            <p className="ticket-description">
              {ticket.description}
            </p>

          </div>
        )}


        <div className="ticket-metadata-grid">

          <div>

            <span>
              Approval
            </span>

            <strong>
              {formatLabel(
                ticket.approval_status
              )}
            </strong>

          </div>


          <div>

            <span>
              Severity
            </span>

            <strong>
              {formatLabel(
                ticket.severity
              )}
            </strong>

          </div>


          <div>

            <span>
              Workflow
            </span>

            <strong>
              {formatLabel(
                ticket.status
              )}
            </strong>

          </div>


          <div>

            <span>
              Monday
            </span>

            <strong>
              {ticket.monday_item_id
                ? "Synchronized"
                : "Not synchronized"}
            </strong>

          </div>

        </div>


        {ticket.monday_item_id && (
          <div className="integration-status">

            <div className="integration-icon">
              M
            </div>

            <div>

              <strong>
                Monday.com synchronized
              </strong>

              <span>
                Item ID:{" "}
                {ticket.monday_item_id}
              </span>

            </div>

          </div>
        )}


        {ticket.failure_reason && (
          <div className="alert alert-error ticket-alert">

            <div>

              <strong>
                Execution failure
              </strong>

              <span>
                {ticket.failure_reason}
              </span>

            </div>

          </div>
        )}


        <div className="ticket-card-footer">

          <div className="ticket-id-full">

            <span>
              ID
            </span>

            <code>
              {ticket.id}
            </code>

          </div>


          <div className="ticket-actions">

            {pendingApproval && (
              <>

                <button
                  type="button"
                  className="approve-button"
                  disabled={
                    isProcessing
                  }
                  onClick={() =>
                    handleReview(
                      ticket.id,
                      true
                    )
                  }
                >
                  {isProcessing
                    ? "Processing..."
                    : "✓ Approve"}
                </button>


                <button
                  type="button"
                  className="reject-button"
                  disabled={
                    isProcessing
                  }
                  onClick={() =>
                    handleReview(
                      ticket.id,
                      false
                    )
                  }
                >
                  {isProcessing
                    ? "Processing..."
                    : "Reject"}
                </button>

              </>
            )}


            {canExecute && (
              <button
                type="button"
                className="execute-button"
                disabled={
                  isProcessing
                }
                onClick={() =>
                  handleExecute(
                    ticket.id
                  )
                }
              >
                {isProcessing
                  ? "Executing..."
                  : "Execute →"}
              </button>
            )}

          </div>

        </div>

      </article>
    );
  };


  /* =======================================================
     LOADING
     ======================================================= */

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


  /* =======================================================
     PAGE
     ======================================================= */

  return (
    <div className="app-page staff-app-page">

      <div className="background-orb app-orb-one" />
      <div className="background-orb app-orb-two" />


      <nav className="topbar">

        <div className="topbar-inner">

          <div className="brand-mark">

            <div className="brand-icon brand-icon-small">
              H
            </div>

            <div>
              <span className="brand-name">
                Harbor
              </span>

              <span className="brand-caption">
                Operations
              </span>
            </div>

          </div>


          <div className="topbar-center">

            <span className="live-indicator">

              <span className="status-dot" />

              Support Operations

            </span>

          </div>


          <div className="topbar-actions">

            <div className="user-chip">

              <div className="avatar">
                {user?.email
                  ?.charAt(0)
                  ?.toUpperCase()
                  || "S"}
              </div>

              <div className="user-chip-copy">

                <strong>
                  {user?.email}
                </strong>

                <span>
                  Support Agent
                </span>

              </div>

            </div>


            <button
              type="button"
              className="ghost-button"
              onClick={logout}
            >
              Logout
            </button>

          </div>

        </div>

      </nav>


      <main className="staff-page">

        <section className="staff-hero">

          <div>

            <span className="eyebrow">
              OPERATIONS CONSOLE
            </span>

            <h1>
              Support Operations
            </h1>

            <p>
              Review customer escalations,
              approve actions, execute verified
              requests, and monitor processed cases.
            </p>

          </div>


          <button
            type="button"
            className="secondary-button refresh-button"
            onClick={() =>
              loadTickets(true)
            }
            disabled={refreshing}
          >
            ↻{" "}
            {refreshing
              ? "Refreshing..."
              : "Refresh queue"}
          </button>

        </section>


        <section className="stats-grid">

          <div className="stat-card glass-card">

            <div className="stat-icon stat-icon-primary">
              ◎
            </div>

            <div>

              <span>
                Total tickets
              </span>

              <strong>
                {statistics.total}
              </strong>

            </div>

          </div>


          <div className="stat-card glass-card">

            <div className="stat-icon stat-icon-warning">
              ◷
            </div>

            <div>

              <span>
                Pending review
              </span>

              <strong>
                {statistics.pending}
              </strong>

            </div>

          </div>


          <div className="stat-card glass-card">

            <div className="stat-icon stat-icon-primary">
              ✓
            </div>

            <div>

              <span>
                Approved
              </span>

              <strong>
                {statistics.approved}
              </strong>

            </div>

          </div>


          <div className="stat-card glass-card">

            <div className="stat-icon stat-icon-success">
              ✓
            </div>

            <div>

              <span>
                Successful
              </span>

              <strong>
                {statistics.successful}
              </strong>

            </div>

          </div>

        </section>


        {error && (
          <div className="alert alert-error">

            <div>

              <strong>
                Operation failed
              </strong>

              <span>
                {error}
              </span>

            </div>

          </div>
        )}


        {successMessage && (
          <div className="alert alert-success">

            <div>

              <strong>
                Success
              </strong>

              <span>
                {successMessage}
              </span>

            </div>

          </div>
        )}


        {/* =================================================
            SEARCH + FILTER
            ================================================= */}

        <section className="staff-filter-bar glass-card">

          <div className="staff-search-box">

            <span className="staff-search-icon">
              ⌕
            </span>

            <input
              type="text"
              value={searchQuery}
              onChange={(event) =>
                setSearchQuery(
                  event.target.value
                )
              }
              placeholder="Search customer, email, ticket ID, title..."
            />

          </div>


          <div className="staff-filter-actions">

            <label className="staff-filter-select">

              <span>
                Severity
              </span>

              <select
                value={
                  severityFilter
                }
                onChange={(event) =>
                  setSeverityFilter(
                    event.target.value
                  )
                }
              >
                <option value="all">
                  All severities
                </option>

                <option value="low">
                  Low
                </option>

                <option value="medium">
                  Medium
                </option>

                <option value="high">
                  High
                </option>

                <option value="critical">
                  Critical
                </option>
              </select>

            </label>


            {(searchQuery
              || severityFilter
              !== "all") && (
              <button
                type="button"
                className="clear-filter-button"
                onClick={
                  clearFilters
                }
              >
                Clear
              </button>
            )}

          </div>

        </section>


        {/* =================================================
            WORKFLOW TABS
            ================================================= */}

        <div className="staff-view-tabs">

          <button
            type="button"
            className={
              activeTab === "pending"
                ? "staff-view-tab staff-view-tab-active"
                : "staff-view-tab"
            }
            onClick={() =>
              setActiveTab(
                "pending"
              )
            }
          >
            Pending Review

            <span className="staff-tab-count">
              {groups.pending.length}
            </span>
          </button>


          <button
            type="button"
            className={
              activeTab === "approved"
                ? "staff-view-tab staff-view-tab-active"
                : "staff-view-tab"
            }
            onClick={() =>
              setActiveTab(
                "approved"
              )
            }
          >
            Approved

            <span className="staff-tab-count">
              {groups.approved.length}
            </span>
          </button>


          <button
            type="button"
            className={
              activeTab === "successful"
                ? "staff-view-tab staff-view-tab-active"
                : "staff-view-tab"
            }
            onClick={() =>
              setActiveTab(
                "successful"
              )
            }
          >
            Successful

            <span className="staff-tab-count">
              {groups.successful.length}
            </span>
          </button>


          <button
            type="button"
            className={
              activeTab === "rejected"
                ? "staff-view-tab staff-view-tab-active"
                : "staff-view-tab"
            }
            onClick={() =>
              setActiveTab(
                "rejected"
              )
            }
          >
            Rejected / Failed

            <span className="staff-tab-count">
              {groups.rejected.length}
            </span>
          </button>

        </div>


        {/* =================================================
            ACTIVE TAB PANEL
            ================================================= */}

        <section className="staff-tab-panel glass-card">

          <div className="staff-tab-panel-header">

            <div>

              <h2>
                {
                  tabConfig[
                    activeTab
                  ].title
                }
              </h2>

              <p>
                {
                  tabConfig[
                    activeTab
                  ].description
                }
              </p>

            </div>


            <span className="staff-panel-count">
              {filteredActiveGroup.length}

              {" "}

              {filteredActiveGroup.length === 1
                ? "ticket"
                : "tickets"}
            </span>

          </div>


          {filteredActiveGroup.length === 0
            ? (
              <div className="staff-tab-empty">

                <div className="staff-tab-empty-icon">
                  ⌕
                </div>

                <h3>
                  No matching tickets
                </h3>

                <p>
                  {searchQuery
                    || severityFilter !== "all"
                    ? (
                      "Try changing your search "
                      + "or severity filter."
                    )
                    : (
                      "No tickets are currently "
                      + "in this workflow stage."
                    )}
                </p>

                {(searchQuery
                  || severityFilter
                  !== "all") && (
                  <button
                    type="button"
                    className="secondary-button staff-empty-clear"
                    onClick={
                      clearFilters
                    }
                  >
                    Clear filters
                  </button>
                )}

              </div>
            )
            : (
              <div className="ticket-list">

                {filteredActiveGroup.map(
                  renderTicketCard
                )}

              </div>
            )}

        </section>

      </main>

    </div>
  );
}
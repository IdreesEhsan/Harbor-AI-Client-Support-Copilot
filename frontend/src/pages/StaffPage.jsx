import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  addInternalNote,
  executeTicket,
  getTicketUpdates,
  getTickets,
  replyToTicket,
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


  /* =======================================================
     TICKET STATE
     ======================================================= */

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
     CONVERSATION STATE
     ======================================================= */

  const [
    expandedTicketId,
    setExpandedTicketId,
  ] = useState(null);

  const [
    ticketUpdates,
    setTicketUpdates,
  ] = useState([]);

  const [
    updatesLoading,
    setUpdatesLoading,
  ] = useState(false);

  const [
    updateMode,
    setUpdateMode,
  ] = useState("reply");

  const [
    updateContent,
    setUpdateContent,
  ] = useState("");

  const [
    updateSubmitting,
    setUpdateSubmitting,
  ] = useState(false);

  const [
    updateError,
    setUpdateError,
  ] = useState("");


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
          setRefreshing(
            true
          );
        }


        try {
          const data =
            await getTickets();


          setTickets(
            Array.isArray(
              data
            )
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
          setLoading(
            false
          );

          setRefreshing(
            false
          );
        }
      },
      []
    );


  useEffect(() => {
    loadTickets();
  }, [
    loadTickets,
  ]);


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


        setExpandedTicketId(
          null
        );

        setTicketUpdates([]);


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
     EXECUTE TICKET
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


        setExpandedTicketId(
          null
        );

        setTicketUpdates([]);


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
     LOAD TICKET CONVERSATION
     ======================================================= */

  const loadTicketUpdates =
    async (
      ticketId
    ) => {
      setUpdatesLoading(
        true
      );

      setUpdateError("");


      try {
        const data =
          await getTicketUpdates(
            ticketId
          );


        setTicketUpdates(
          Array.isArray(
            data
          )
            ? data
            : []
        );

      } catch (err) {
        console.error(
          "Unable to load ticket updates:",
          err
        );


        setUpdateError(
          err.response?.data?.detail
          || "Unable to load ticket conversation."
        );

      } finally {
        setUpdatesLoading(
          false
        );
      }
    };


  /* =======================================================
     OPEN / CLOSE CONVERSATION
     ======================================================= */

  const toggleConversation =
    async (
      ticketId
    ) => {
      if (
        expandedTicketId
        === ticketId
      ) {
        setExpandedTicketId(
          null
        );

        setTicketUpdates([]);

        setUpdateContent("");

        setUpdateError("");

        return;
      }


      setExpandedTicketId(
        ticketId
      );

      setUpdateMode(
        "reply"
      );

      setUpdateContent("");

      setUpdateError("");


      await loadTicketUpdates(
        ticketId
      );
    };


  /* =======================================================
     SEND REPLY / INTERNAL NOTE
     ======================================================= */

  const submitTicketUpdate =
    async (
      event,
      ticketId
    ) => {
      event.preventDefault();


      const content =
        updateContent.trim();


      if (
        !content
        || updateSubmitting
      ) {
        return;
      }


      setUpdateSubmitting(
        true
      );

      setUpdateError("");

      setSuccessMessage("");


      try {
        let newUpdate;


        /* -------------------------------------------------
           INTERNAL NOTE
           ------------------------------------------------- */

        if (
          updateMode
          === "internal_note"
        ) {
          newUpdate =
            await addInternalNote(
              ticketId,
              content
            );


          setSuccessMessage(
            "Internal note added."
          );
        }


        /* -------------------------------------------------
           CUSTOMER-VISIBLE STAFF REPLY
           ------------------------------------------------- */

        else {
          newUpdate =
            await replyToTicket(
              ticketId,
              content
            );


          setSuccessMessage(
            "Reply sent to customer."
          );
        }


        /* =================================================
           IMPORTANT PERFORMANCE IMPROVEMENT

           Previously:

           POST message
               ↓
           wait
               ↓
           GET entire conversation
               ↓
           wait
               ↓
           render

           Now:

           POST message
               ↓
           backend returns created update
               ↓
           append directly into React state
               ↓
           message appears immediately
           ================================================= */

        setTicketUpdates(
          (current) => [
            ...current,
            newUpdate,
          ]
        );


        setUpdateContent("");


      } catch (err) {
        console.error(
          "Unable to create ticket update:",
          err
        );


        setUpdateError(
          err.response?.data?.detail
          || "Unable to add ticket update."
        );

      } finally {
        setUpdateSubmitting(
          false
        );
      }
    };


  /* =======================================================
     FORMATTING HELPERS
     ======================================================= */

  const formatLabel = (
    value
  ) => {
    if (!value) {
      return "Unknown";
    }


    return String(
      value
    )
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


  const formatDate = (
    value
  ) => {
    if (!value) {
      return "";
    }


    const date =
      new Date(
        value
      );


    if (
      Number.isNaN(
        date.getTime()
      )
    ) {
      return "";
    }


    return (
      date.toLocaleString(
        undefined,
        {
          month:
            "short",

          day:
            "numeric",

          year:
            "numeric",

          hour:
            "numeric",

          minute:
            "2-digit",
        }
      )
    );
  };


  const getSeverityClass = (
    severity
  ) => {
    const value =
      String(
        severity
        || ""
      ).toLowerCase();


    if (
      value
      === "critical"
    ) {
      return (
        "badge badge-danger"
      );
    }


    if (
      value === "high"
      || value === "medium"
    ) {
      return (
        "badge badge-warning"
      );
    }


    return (
      "badge badge-success"
    );
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
      return (
        "badge badge-success"
      );
    }


    if (
      status === "rejected"
      || status === "failed"
    ) {
      return (
        "badge badge-danger"
      );
    }


    return (
      "badge badge-warning"
    );
  };


  const getAuthorLabel = (
    update
  ) => {
    if (
      update.update_type
      === "internal_note"
    ) {
      return (
        "Internal Note"
      );
    }


    if (
      update.update_type
      === "customer_reply"
    ) {
      return (
        update.author?.full_name
        || update.author?.email
        || "Customer"
      );
    }


    return (
      update.author?.full_name
      || update.author?.email
      || "Harbor Support"
    );
  };


  /* =======================================================
     WORKFLOW GROUPS
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
              ticket.status
              === "approved"
              || ticket.status
              === "executing"
          ),


        successful:
          tickets.filter(
            (ticket) =>
              ticket.status
              === "open"
              || ticket.status
              === "in_progress"
              || ticket.status
              === "resolved"
              || ticket.status
              === "closed"
          ),


        rejected:
          tickets.filter(
            (ticket) =>
              ticket.status
              === "rejected"
              || ticket.status
              === "failed"
          ),
      }),
      [
        tickets,
      ]
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


        return (
          currentGroup.filter(
            (ticket) => {
              const searchableText = [
                ticket.id,
                ticket.title,
                ticket.description,
                ticket.customer?.full_name,
                ticket.customer?.email,
                ticket.customer?.country,
              ]
                .filter(
                  Boolean
                )
                .join(
                  " "
                )
                .toLowerCase();


              const matchesSearch =
                !query
                || searchableText.includes(
                  query
                );


              const matchesSeverity =
                severityFilter
                === "all"
                || ticket.severity
                === severityFilter;


              return (
                matchesSearch
                && matchesSeverity
              );
            }
          )
        );
      },
      [
        activeTab,
        groups,
        searchQuery,
        severityFilter,
      ]
    );


  /* =======================================================
     DASHBOARD STATS
     ======================================================= */

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


  /* =======================================================
     TAB CONFIGURATION
     ======================================================= */

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
        "Approved tickets ready for controlled execution.",
    },


    successful: {
      title:
        "Successful / Processed",

      description:
        "Processed tickets progressing through support.",
    },


    rejected: {
      title:
        "Rejected / Failed",

      description:
        "Rejected tickets or tickets that could not be completed.",
    },
  };


  const clearFilters = () => {
    setSearchQuery("");

    setSeverityFilter(
      "all"
    );
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
        .charAt(
          0
        )
        .toUpperCase();


    const conversationOpen =
      expandedTicketId
      === ticket.id;


    return (
      <article
        key={
          ticket.id
        }
        className="ticket-card"
      >

        {/* =================================================
            HEADER
            ================================================= */}

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


        {/* =================================================
            CUSTOMER INFORMATION
            ================================================= */}

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


        {/* =================================================
            CUSTOMER REQUEST
            ================================================= */}

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


        {/* =================================================
            METADATA
            ================================================= */}

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


        {/* =================================================
            MONDAY STATUS
            ================================================= */}

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


        {/* =================================================
            FAILURE
            ================================================= */}

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


        {/* =================================================
            ACTIONS
            ================================================= */}

        <div className="ticket-card-footer">

          <div className="ticket-footer-left">

            <button
              type="button"
              className="ticket-conversation-button"
              onClick={() =>
                toggleConversation(
                  ticket.id
                )
              }
            >
              {conversationOpen
                ? "Hide conversation"
                : "💬 Conversation"}
            </button>

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


        {/* =================================================
            TICKET ID
            ================================================= */}

        <div className="ticket-id-full">

          <span>
            Ticket ID
          </span>

          <code>
            {ticket.id}
          </code>

        </div>


        {/* =================================================
            CONVERSATION PANEL
            ================================================= */}

        {conversationOpen && (
          <div className="ticket-conversation-panel">

            <div className="ticket-conversation-header">

              <div>

                <h4>
                  Case Conversation
                </h4>

                <p>
                  Customer messages, staff replies,
                  and private internal notes.
                </p>

              </div>


              <button
                type="button"
                className="conversation-refresh-button"
                onClick={() =>
                  loadTicketUpdates(
                    ticket.id
                  )
                }
                aria-label="Refresh conversation"
              >
                ↻
              </button>

            </div>


            {/* ---------------------------------------------
                LOADING
                --------------------------------------------- */}

            {updatesLoading
              ? (
                <div className="conversation-loading">
                  Loading conversation...
                </div>
              )


              /* -------------------------------------------
                 EMPTY
                 ------------------------------------------- */

              : ticketUpdates.length
                === 0
                ? (
                  <div className="conversation-empty">
                    No conversation messages yet.
                  </div>
                )


                /* -----------------------------------------
                   UPDATE LIST
                   ----------------------------------------- */

                : (
                  <div className="ticket-update-list">

                    {ticketUpdates.map(
                      (update) => {
                        const internal =
                          update.update_type
                          === "internal_note";


                        const customerReply =
                          update.update_type
                          === "customer_reply";


                        return (
                          <div
                            key={
                              update.id
                            }
                            className={
                              internal
                                ? (
                                  "ticket-update "
                                  + "ticket-update-internal"
                                )
                                : customerReply
                                  ? (
                                    "ticket-update "
                                    + "ticket-update-customer"
                                  )
                                  : (
                                    "ticket-update "
                                    + "ticket-update-staff"
                                  )
                            }
                          >

                            <div className="ticket-update-top">

                              <strong>
                                {getAuthorLabel(
                                  update
                                )}
                              </strong>


                              <span>
                                {formatDate(
                                  update.created_at
                                )}
                              </span>

                            </div>


                            <p>
                              {update.content}
                            </p>


                            {internal && (
                              <span className="internal-note-label">
                                Staff only
                              </span>
                            )}

                          </div>
                        );
                      }
                    )}

                  </div>
                )}


            {/* ---------------------------------------------
                ERROR
                --------------------------------------------- */}

            {updateError && (
              <div className="conversation-error">
                {updateError}
              </div>
            )}


            {/* ---------------------------------------------
                REPLY / INTERNAL NOTE TABS
                --------------------------------------------- */}

            <div className="ticket-update-mode-tabs">

              <button
                type="button"
                className={
                  updateMode
                  === "reply"
                    ? (
                      "update-mode-button "
                      + "update-mode-button-active"
                    )
                    : "update-mode-button"
                }
                onClick={() =>
                  setUpdateMode(
                    "reply"
                  )
                }
              >
                Reply to customer
              </button>


              <button
                type="button"
                className={
                  updateMode
                  === "internal_note"
                    ? (
                      "update-mode-button "
                      + "update-mode-button-active"
                    )
                    : "update-mode-button"
                }
                onClick={() =>
                  setUpdateMode(
                    "internal_note"
                  )
                }
              >
                Internal note
              </button>

            </div>


            {/* ---------------------------------------------
                MESSAGE COMPOSER
                --------------------------------------------- */}

            <form
              className="ticket-update-composer"
              onSubmit={(event) =>
                submitTicketUpdate(
                  event,
                  ticket.id
                )
              }
            >

              <textarea
                rows="3"
                value={
                  updateContent
                }
                onChange={(event) =>
                  setUpdateContent(
                    event.target.value
                  )
                }
                placeholder={
                  updateMode
                  === "internal_note"
                    ? (
                      "Add a private note "
                      + "for support staff..."
                    )
                    : (
                      "Write a reply "
                      + "to the customer..."
                    )
                }
                disabled={
                  updateSubmitting
                }
              />


              <div className="ticket-update-composer-footer">

                <span>
                  {updateMode
                  === "internal_note"
                    ? (
                      "Only support staff "
                      + "can see this note."
                    )
                    : (
                      "The customer will "
                      + "see this reply."
                    )}
                </span>


                <button
                  type="submit"
                  className={
                    updateMode
                    === "internal_note"
                      ? "internal-note-submit"
                      : "reply-submit"
                  }
                  disabled={
                    updateSubmitting
                    || !updateContent.trim()
                  }
                >
                  {updateSubmitting
                    ? "Saving..."
                    : updateMode
                      === "internal_note"
                        ? "Add note"
                        : "Send reply"}
                </button>

              </div>

            </form>

          </div>
        )}

      </article>
    );
  };


  /* =======================================================
     LOADING SCREEN
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


      {/* ===================================================
          TOP BAR
          =================================================== */}

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
                  ?.charAt(
                    0
                  )
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
              onClick={
                logout
              }
            >
              Logout
            </button>

          </div>

        </div>

      </nav>


      {/* ===================================================
          MAIN
          =================================================== */}

      <main className="staff-page">

        {/* =================================================
            HERO
            ================================================= */}

        <section className="staff-hero">

          <div>

            <span className="eyebrow">
              OPERATIONS CONSOLE
            </span>


            <h1>
              Support Operations
            </h1>


            <p>
              Review escalations, communicate
              with customers, approve actions,
              and monitor support workflows.
            </p>

          </div>


          <button
            type="button"
            className="secondary-button refresh-button"
            onClick={() =>
              loadTickets(
                true
              )
            }
            disabled={
              refreshing
            }
          >
            ↻{" "}
            {refreshing
              ? "Refreshing..."
              : "Refresh queue"}
          </button>

        </section>


        {/* =================================================
            STATS
            ================================================= */}

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


        {/* =================================================
            ALERTS
            ================================================= */}

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
            SEARCH / FILTER
            ================================================= */}

        <section className="staff-filter-bar glass-card">

          <div className="staff-search-box">

            <span className="staff-search-icon">
              ⌕
            </span>


            <input
              type="text"
              value={
                searchQuery
              }
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

          {[
            [
              "pending",
              "Pending Review",
            ],

            [
              "approved",
              "Approved",
            ],

            [
              "successful",
              "Successful",
            ],

            [
              "rejected",
              "Rejected / Failed",
            ],
          ].map(
            ([
              key,
              label,
            ]) => (
              <button
                key={
                  key
                }
                type="button"
                className={
                  activeTab
                  === key
                    ? (
                      "staff-view-tab "
                      + "staff-view-tab-active"
                    )
                    : "staff-view-tab"
                }
                onClick={() => {
                  setActiveTab(
                    key
                  );

                  setExpandedTicketId(
                    null
                  );

                  setTicketUpdates([]);
                }}
              >

                {label}


                <span className="staff-tab-count">
                  {
                    groups[
                      key
                    ].length
                  }
                </span>

              </button>
            )
          )}

        </div>


        {/* =================================================
            ACTIVE TAB
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
              {filteredActiveGroup.length
              === 1
                ? "ticket"
                : "tickets"}
            </span>

          </div>


          {filteredActiveGroup.length
          === 0
            ? (
              <div className="staff-tab-empty">

                <div className="staff-tab-empty-icon">
                  ✓
                </div>


                <h3>
                  Nothing here
                </h3>


                <p>
                  No matching tickets are
                  currently in this workflow stage.
                </p>

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
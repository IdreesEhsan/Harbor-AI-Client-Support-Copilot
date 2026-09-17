import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
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

import {
  connectNotificationSocket,
} from "../realtime/notifications";

import "../styles/notifications.css";


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


  const [
    messageNotifications,
    setMessageNotifications,
  ] = useState([]);

  const [
    notificationMenuOpen,
    setNotificationMenuOpen,
  ] = useState(false);

  const [
    unreadByTicket,
    setUnreadByTicket,
  ] = useState({});


  const expandedTicketIdRef =
    useRef(null);

  const notificationMenuRef =
    useRef(null);


  useEffect(() => {
    expandedTicketIdRef.current =
      expandedTicketId;
  }, [
    expandedTicketId,
  ]);


  useEffect(() => {
    const handleOutsideClick =
      (
        event
      ) => {
        if (
          notificationMenuRef.current
          && !notificationMenuRef
            .current
            .contains(
              event.target
            )
        ) {
          setNotificationMenuOpen(
            false
          );
        }
      };


    document.addEventListener(
      "mousedown",
      handleOutsideClick
    );


    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick
      );
    };
  }, []);


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
          setError(
            err.response
              ?.data
              ?.detail
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


  /*
   * REALTIME STAFF NOTIFICATIONS.
   *
   * No polling.
   * No notification HTTP endpoint.
   */

  useEffect(() => {
    if (
      !user
      || ![
        "support_agent",
        "admin",
      ].includes(
        user.role
      )
    ) {
      return undefined;
    }


    const disconnect =
      connectNotificationSocket({
        onMessage:
          (
            notification
          ) => {
            if (
              notification?.type
              !== "ticket_message"
              || notification?.recipient
              !== "staff"
              || notification?.update_type
              !== "customer_reply"
            ) {
              return;
            }


            const ticketId =
              notification.ticket_id;


            if (!ticketId) {
              return;
            }


            setMessageNotifications(
              (current) => {
                if (
                  current.some(
                    (item) =>
                      item.id
                      === notification.id
                  )
                ) {
                  return current;
                }


                return [
                  notification,
                  ...current,
                ].slice(
                  0,
                  30
                );
              }
            );


            if (
              expandedTicketIdRef.current
              === ticketId
            ) {
              setTicketUpdates(
                (current) => {
                  if (
                    current.some(
                      (update) =>
                        update.id
                        === notification.id
                    )
                  ) {
                    return current;
                  }


                  return [
                    ...current,
                    notification,
                  ];
                }
              );


              return;
            }


            setUnreadByTicket(
              (current) => ({
                ...current,

                [ticketId]:
                  (
                    current[
                      ticketId
                    ]
                    || 0
                  )
                  + 1,
              })
            );
          },

        onReady:
          () => {
            console.log(
              "Harbor staff realtime ready."
            );
          },

        onError:
          (
            event
          ) => {
            console.error(
              "Harbor staff realtime error:",
              event
            );
          },
      });


    return disconnect;

  }, [
    user,
  ]);


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
        setError(
          err.response
            ?.data
            ?.detail
          || "Unable to review the support ticket."
        );

      } finally {
        setProcessingTicketId(
          null
        );
      }
    };


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
        setError(
          err.response
            ?.data
            ?.detail
          || "Unable to execute the support ticket."
        );

      } finally {
        setProcessingTicketId(
          null
        );
      }
    };


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
        setUpdateError(
          err.response
            ?.data
            ?.detail
          || "Unable to load ticket conversation."
        );

      } finally {
        setUpdatesLoading(
          false
        );
      }
    };


  const markTicketRead =
    (
      ticketId
    ) => {
      setUnreadByTicket(
        (current) => ({
          ...current,

          [ticketId]:
            0,
        })
      );
    };


  const toggleConversation =
    async (
      ticketId
    ) => {
      markTicketRead(
        ticketId
      );


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

        } else {
          newUpdate =
            await replyToTicket(
              ticketId,
              content
            );


          setSuccessMessage(
            "Reply sent to customer."
          );
        }


        setTicketUpdates(
          (current) => [
            ...current,
            newUpdate,
          ]
        );


        setUpdateContent("");

      } catch (err) {
        setUpdateError(
          err.response
            ?.data
            ?.detail
          || "Unable to add ticket update."
        );

      } finally {
        setUpdateSubmitting(
          false
        );
      }
    };


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
        (
          character
        ) =>
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


    return date.toLocaleString(
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
    );
  };


  const formatRelativeTime = (
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


    const difference =
      Date.now()
      - date.getTime();


    if (
      difference
      < 60000
    ) {
      return "Now";
    }


    if (
      difference
      < 3600000
    ) {
      return (
        `${Math.floor(
          difference
          / 60000
        )}m`
      );
    }


    if (
      difference
      < 86400000
    ) {
      return (
        `${Math.floor(
          difference
          / 3600000
        )}h`
      );
    }


    return (
      `${Math.floor(
        difference
        / 86400000
      )}d`
    );
  };


  const getSeverityClass = (
    severity
  ) => {
    if (
      severity
      === "critical"
    ) {
      return (
        "badge badge-danger"
      );
    }


    if (
      severity === "high"
      || severity === "medium"
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
      [
        "open",
        "in_progress",
        "resolved",
        "closed",
      ].includes(
        status
      )
    ) {
      return (
        "badge badge-success"
      );
    }


    if (
      [
        "rejected",
        "failed",
      ].includes(
        status
      )
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
      return "Internal Note";
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
              [
                "approved",
                "executing",
              ].includes(
                ticket.status
              )
          ),

        successful:
          tickets.filter(
            (ticket) =>
              [
                "open",
                "in_progress",
                "resolved",
                "closed",
              ].includes(
                ticket.status
              )
          ),

        rejected:
          tickets.filter(
            (ticket) =>
              [
                "rejected",
                "failed",
              ].includes(
                ticket.status
              )
          ),
      }),
      [
        tickets,
      ]
    );


  const filteredActiveGroup =
    useMemo(
      () => {
        const query =
          searchQuery
            .trim()
            .toLowerCase();


        return (
          groups[
            activeTab
          ]
          || []
        ).filter(
          (
            ticket
          ) => {
            const searchableText = [
              ticket.id,
              ticket.title,
              ticket.description,
              ticket.customer
                ?.full_name,
              ticket.customer
                ?.email,
              ticket.customer
                ?.country,
            ]
              .filter(
                Boolean
              )
              .join(
                " "
              )
              .toLowerCase();


            return (
              (
                !query
                || searchableText.includes(
                  query
                )
              )
              && (
                severityFilter
                === "all"
                || ticket.severity
                === severityFilter
              )
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


  const totalUnreadNotifications =
    useMemo(
      () =>
        Object.values(
          unreadByTicket
        ).reduce(
          (
            total,
            count
          ) =>
            total
            + Number(
              count
              || 0
            ),
          0
        ),
      [
        unreadByTicket,
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


  const clearFilters =
    () => {
      setSearchQuery("");

      setSeverityFilter(
        "all"
      );
    };


  const getStaffTabForStatus =
    (
      status
    ) => {
      if (
        status
        === "pending_approval"
      ) {
        return "pending";
      }


      if (
        [
          "approved",
          "executing",
        ].includes(
          status
        )
      ) {
        return "approved";
      }


      if (
        [
          "rejected",
          "failed",
        ].includes(
          status
        )
      ) {
        return "rejected";
      }


      return "successful";
    };


  const openTicketFromNotification =
    async (
      notification
    ) => {
      const ticketId =
        notification.ticket_id;


      if (!ticketId) {
        return;
      }


      setNotificationMenuOpen(
        false
      );

      markTicketRead(
        ticketId
      );

      setSearchQuery("");

      setSeverityFilter(
        "all"
      );

      setActiveTab(
        getStaffTabForStatus(
          notification.ticket
            ?.status
        )
      );

      setExpandedTicketId(
        ticketId
      );

      setUpdateMode(
        "reply"
      );


      await Promise.all([
        loadTickets(),

        loadTicketUpdates(
          ticketId
        ),
      ]);
    };


  const renderTicketCard =
    (
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
        && [
          "approved",
          "executing",
        ].includes(
          ticket.status
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

      const conversationOpen =
        expandedTicketId
        === ticket.id;

      const unreadCount =
        unreadByTicket[
          ticket.id
        ]
        || 0;


      return (
        <article
          key={
            ticket.id
          }
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

            <div className="ticket-footer-left">

              <button
                type="button"
                className="ticket-conversation-button ticket-conversation-button-unread"
                onClick={() =>
                  toggleConversation(
                    ticket.id
                  )
                }
              >

                <span>
                  {conversationOpen
                    ? "Hide conversation"
                    : "💬 Conversation"}
                </span>


                {!conversationOpen
                  && unreadCount > 0
                  && (
                    <span className="conversation-unread-badge">

                      {unreadCount > 9
                        ? "9+"
                        : unreadCount}

                    </span>
                  )}

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


          <div className="ticket-id-full">

            <span>
              Ticket ID
            </span>

            <code>
              {ticket.id}
            </code>

          </div>


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
                >
                  ↻
                </button>

              </div>


              {updatesLoading
                ? (
                  <div className="conversation-loading">
                    Loading conversation...
                  </div>
                )

                : ticketUpdates.length === 0
                  ? (
                    <div className="conversation-empty">
                      No conversation messages yet.
                    </div>
                  )

                  : (
                    <div className="ticket-update-list">

                      {ticketUpdates.map(
                        (
                          update
                        ) => {
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


              {updateError && (
                <div className="conversation-error">
                  {updateError}
                </div>
              )}


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
                      ? "Add a private note for support staff..."
                      : "Write a reply to the customer..."
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

            <div
              className="notification-menu-wrapper"
              ref={
                notificationMenuRef
              }
            >

              <button
                type="button"
                className="notification-bell-button"
                onClick={() =>
                  setNotificationMenuOpen(
                    (
                      current
                    ) =>
                      !current
                  )
                }
                aria-label="Notifications"
              >
                🔔


                {totalUnreadNotifications > 0 && (
                  <span className="notification-bell-badge">

                    {totalUnreadNotifications > 9
                      ? "9+"
                      : totalUnreadNotifications}

                  </span>
                )}

              </button>


              {notificationMenuOpen && (
                <div className="notification-dropdown">

                  <div className="notification-dropdown-header">

                    <div>

                      <strong>
                        Notifications
                      </strong>

                      <span>
                        Customer messages
                      </span>

                    </div>


                    {totalUnreadNotifications > 0 && (
                      <span className="notification-dropdown-count">
                        {totalUnreadNotifications}
                      </span>
                    )}

                  </div>


                  <div className="notification-dropdown-list">

                    {messageNotifications.length === 0
                      ? (
                        <div className="notification-dropdown-empty">

                          <div>
                            ✓
                          </div>

                          <strong>
                            You're all caught up
                          </strong>

                          <span>
                            New customer replies will appear here.
                          </span>

                        </div>
                      )

                      : messageNotifications.map(
                        (
                          notification
                        ) => {
                          const ticketId =
                            notification.ticket_id;

                          const unread =
                            (
                              unreadByTicket[
                                ticketId
                              ]
                              || 0
                            ) > 0;

                          const customerName =
                            notification
                              .author
                              ?.full_name
                            || notification
                              .author
                              ?.email
                            || "Customer";


                          return (
                            <button
                              key={
                                notification.id
                              }
                              type="button"
                              className={
                                unread
                                  ? (
                                    "notification-dropdown-item "
                                    + "notification-dropdown-item-unread"
                                  )
                                  : "notification-dropdown-item"
                              }
                              onClick={() =>
                                openTicketFromNotification(
                                  notification
                                )
                              }
                            >

                              <div className="notification-dropdown-avatar">

                                {customerName
                                  .charAt(
                                    0
                                  )
                                  .toUpperCase()}

                              </div>


                              <div className="notification-dropdown-copy">

                                <div className="notification-dropdown-title">

                                  <strong>
                                    {customerName}
                                  </strong>


                                  {unread && (
                                    <span className="notification-unread-dot" />
                                  )}

                                </div>


                                <p>
                                  {notification.content}
                                </p>


                                <div className="notification-dropdown-footer">

                                  <span>
                                    {notification.ticket?.title
                                      || "Support Ticket"}
                                  </span>

                                  <span>
                                    {formatRelativeTime(
                                      notification.created_at
                                    )}
                                  </span>

                                </div>

                              </div>

                            </button>
                          );
                        }
                      )}

                  </div>

                </div>
              )}

            </div>


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
              onClick={
                logout
              }
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
              Review escalations, communicate with customers,
              approve actions, and monitor support workflows.
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


        <section className="stats-grid">

          <div className="stat-card glass-card">
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
            {error}
          </div>
        )}


        {successMessage && (
          <div className="alert alert-success">
            {successMessage}
          </div>
        )}


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
                Nothing here.
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
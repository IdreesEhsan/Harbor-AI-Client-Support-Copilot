import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  streamAgentChat,
} from "../api/agent";

import {
  getMyCaseUpdates,
  getMyCases,
  replyToMyCase,
} from "../api/tickets";

import {
  useAuth,
} from "../context/AuthContext";


export default function ChatPage() {
  const {
    user,
    logout,
  } = useAuth();


  /* =======================================================
     MAIN VIEW
     ======================================================= */

  const [
    activeView,
    setActiveView,
  ] = useState("chat");


  const [
    activeCaseTab,
    setActiveCaseTab,
  ] = useState("pending");


  /* =======================================================
     CHAT STATE
     ======================================================= */

  const [
    messages,
    setMessages,
  ] = useState([]);

  const [
    input,
    setInput,
  ] = useState("");

  const [
    conversationId,
    setConversationId,
  ] = useState("");

  const [
    sending,
    setSending,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");


  const messagesEndRef =
    useRef(null);


  /* =======================================================
     MY CASES STATE
     ======================================================= */

  const [
    cases,
    setCases,
  ] = useState([]);

  const [
    casesLoading,
    setCasesLoading,
  ] = useState(false);

  const [
    casesRefreshing,
    setCasesRefreshing,
  ] = useState(false);

  const [
    casesLoaded,
    setCasesLoaded,
  ] = useState(false);

  const [
    casesError,
    setCasesError,
  ] = useState("");


  /* =======================================================
     CASE CONVERSATION
     ======================================================= */

  const [
    expandedCaseId,
    setExpandedCaseId,
  ] = useState(null);

  const [
    caseUpdates,
    setCaseUpdates,
  ] = useState([]);

  const [
    caseUpdatesLoading,
    setCaseUpdatesLoading,
  ] = useState(false);

  const [
    caseReply,
    setCaseReply,
  ] = useState("");

  const [
    caseReplySubmitting,
    setCaseReplySubmitting,
  ] = useState(false);

  const [
    caseConversationError,
    setCaseConversationError,
  ] = useState("");


  /* =======================================================
     AUTO SCROLL
     ======================================================= */

  useEffect(() => {
    if (
      activeView
      === "chat"
    ) {
      messagesEndRef
        .current
        ?.scrollIntoView({
          behavior:
            "smooth",
        });
    }
  }, [
    messages,
    sending,
    activeView,
  ]);


  /* =======================================================
     HELPERS
     ======================================================= */

  const createLocalId = () => {
    if (
      typeof crypto
      !== "undefined"
      && crypto.randomUUID
    ) {
      return (
        crypto.randomUUID()
      );
    }

    return (
      `${Date.now()}-${Math.random()}`
    );
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
        (character) =>
          character.toUpperCase()
      );
  };


  const formatDate = (
    value
  ) => {
    if (!value) {
      return "Unknown";
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
      return "Unknown";
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
      value === "critical"
      || value === "high"
    ) {
      return (
        "badge badge-danger"
      );
    }

    if (
      value === "medium"
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


  /* =======================================================
     CASE GROUPS
     ======================================================= */

  const caseGroups =
    useMemo(
      () => ({
        pending:
          cases.filter(
            (ticket) =>
              ticket.status
              === "pending_approval"
          ),

        approved:
          cases.filter(
            (ticket) =>
              ticket.status
              === "approved"
              || ticket.status
              === "executing"
          ),

        successful:
          cases.filter(
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
          cases.filter(
            (ticket) =>
              ticket.status
              === "rejected"
              || ticket.status
              === "failed"
          ),
      }),
      [cases]
    );


  const activeCaseGroup =
    caseGroups[
      activeCaseTab
    ] || [];


  const caseTabConfig = {
    pending: {
      title:
        "Pending Review",

      description:
        "Support requests waiting for a Harbor support agent to review.",
    },

    approved: {
      title:
        "Approved",

      description:
        "Support requests approved and waiting for processing.",
    },

    successful: {
      title:
        "Successful / Processed",

      description:
        "Support requests successfully processed or currently progressing.",
    },

    rejected: {
      title:
        "Rejected / Failed",

      description:
        "Support requests that were rejected or could not be completed.",
    },
  };


  /* =======================================================
     LOAD CASES
     ======================================================= */

  const loadCases =
    useCallback(
      async (
        refresh = false
      ) => {
        setCasesError("");

        if (refresh) {
          setCasesRefreshing(
            true
          );
        } else {
          setCasesLoading(
            true
          );
        }


        try {
          const data =
            await getMyCases();


          setCases(
            Array.isArray(
              data
            )
              ? data
              : []
          );


          setCasesLoaded(
            true
          );

        } catch (err) {
          console.error(
            "Unable to load customer cases:",
            err
          );


          setCasesError(
            err.response?.data?.detail
            || (
              "Unable to load "
              + "your support cases."
            )
          );

        } finally {
          setCasesLoading(
            false
          );

          setCasesRefreshing(
            false
          );
        }
      },
      []
    );


  const openCases =
    async () => {
      setActiveView(
        "cases"
      );

      if (!casesLoaded) {
        await loadCases();
      }
    };


  /* =======================================================
     CASE CONVERSATION
     ======================================================= */

  const loadCaseUpdates =
    async (
      ticketId
    ) => {
      setCaseUpdatesLoading(
        true
      );

      setCaseConversationError(
        ""
      );


      try {
        const data =
          await getMyCaseUpdates(
            ticketId
          );


        setCaseUpdates(
          Array.isArray(
            data
          )
            ? data
            : []
        );

      } catch (err) {
        console.error(
          "Unable to load case updates:",
          err
        );


        setCaseConversationError(
          err.response?.data?.detail
          || (
            "Unable to load "
            + "case conversation."
          )
        );

      } finally {
        setCaseUpdatesLoading(
          false
        );
      }
    };


  const toggleCaseConversation =
    async (
      ticketId
    ) => {
      if (
        expandedCaseId
        === ticketId
      ) {
        setExpandedCaseId(
          null
        );

        setCaseUpdates([]);
        setCaseReply("");
        setCaseConversationError("");

        return;
      }


      setExpandedCaseId(
        ticketId
      );

      setCaseReply("");
      setCaseConversationError("");


      await loadCaseUpdates(
        ticketId
      );
    };


  /* =======================================================
     IMMEDIATE CUSTOMER REPLY
     ======================================================= */

  const submitCaseReply =
    async (
      event,
      ticketId
    ) => {
      event.preventDefault();


      const content =
        caseReply.trim();


      if (
        !content
        || caseReplySubmitting
      ) {
        return;
      }


      setCaseReplySubmitting(
        true
      );

      setCaseConversationError(
        ""
      );


      try {
        const newUpdate =
          await replyToMyCase(
            ticketId,
            content
          );


        // --------------------------------------------------
        // Append the server-created update immediately.
        // No second GET is required before showing it.
        // --------------------------------------------------

        setCaseUpdates(
          (current) => [
            ...current,
            newUpdate,
          ]
        );


        setCaseReply("");


      } catch (err) {
        console.error(
          "Unable to send customer reply:",
          err
        );


        setCaseConversationError(
          err.response?.data?.detail
          || (
            "Unable to send "
            + "your reply."
          )
        );

      } finally {
        setCaseReplySubmitting(
          false
        );
      }
    };


  /* =======================================================
     STREAMING AI CHAT
     ======================================================= */

  const sendMessage =
    async (
      event
    ) => {
      event.preventDefault();


      const customerMessage =
        input.trim();


      if (
        !customerMessage
        || sending
      ) {
        return;
      }


      const assistantId =
        createLocalId();


      setError("");


      setMessages(
        (current) => [
          ...current,

          {
            id:
              createLocalId(),

            role:
              "user",

            content:
              customerMessage,
          },

          {
            id:
              assistantId,

            role:
              "assistant",

            content:
              "",

            streaming:
              true,

            citations:
              [],
          },
        ]
      );


      setInput("");
      setSending(
        true
      );


      try {

        const data =
          await streamAgentChat({
            message:
              customerMessage,

            conversationId:
              conversationId
              || null,


            onToken:
              (token) => {

                setMessages(
                  (current) =>
                    current.map(
                      (message) => {

                        if (
                          message.id
                          !== assistantId
                        ) {
                          return message;
                        }


                        return {
                          ...message,

                          content:
                            (
                              message.content
                              || ""
                            )
                            + token,
                        };
                      }
                    )
                );
              },
          });


        // --------------------------------------------------
        // Final AgentResponse is canonical.
        //
        // The backend has now completed:
        // - output guardrail
        // - citations
        // - severity
        // - escalation state
        // - ticket confirmation / creation
        // --------------------------------------------------

        setMessages(
          (current) =>
            current.map(
              (message) => {

                if (
                  message.id
                  !== assistantId
                ) {
                  return message;
                }


                return {
                  ...message,

                  content:
                    data.answer,

                  streaming:
                    false,

                  action:
                    data.action,

                  severity:
                    data.severity,

                  citations:
                    data.citations
                    ?? [],

                  escalationRequired:
                    data.escalation_required
                    ?? false,

                  ticketId:
                    data.ticket_id
                    ?? null,

                  ticketStatus:
                    data.ticket_status
                    ?? null,

                  approvalStatus:
                    data.approval_status
                    ?? null,
                };
              }
            )
        );


        if (
          data.conversation_id
        ) {
          setConversationId(
            data.conversation_id
          );
        }


        if (
          data.ticket_id
        ) {
          setCasesLoaded(
            false
          );

          setActiveCaseTab(
            "pending"
          );
        }


      } catch (err) {
        console.error(
          "Harbor streaming request failed:",
          err
        );


        setMessages(
          (current) =>
            current.filter(
              (message) =>
                message.id
                !== assistantId
            )
        );


        setError(
          err.message
          || (
            "Harbor could not "
            + "process your request."
          )
        );


      } finally {
        setSending(
          false
        );
      }
    };


  const handleKeyDown = (
    event
  ) => {
    if (
      event.key
      === "Enter"
      && !event.shiftKey
    ) {
      event.preventDefault();


      if (
        input.trim()
        && !sending
      ) {
        event
          .currentTarget
          .form
          ?.requestSubmit();
      }
    }
  };


  /* =======================================================
     CASE CARD
     ======================================================= */

  const renderCaseCard = (
    ticket
  ) => {
    const conversationOpen =
      expandedCaseId
      === ticket.id;


    return (
      <article
        key={
          ticket.id
        }
        className="customer-case-card"
      >

        <div className="customer-case-top">

          <div className="customer-case-title">

            <div>

              <span className="customer-case-number">
                CASE{" "}
                {String(
                  ticket.id
                )
                  .slice(
                    0,
                    8
                  )
                  .toUpperCase()}
              </span>


              <h3>
                {ticket.title
                  || "Support Case"}
              </h3>

            </div>


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


        {ticket.description && (
          <p className="customer-case-description">
            {ticket.description}
          </p>
        )}


        <div className="customer-case-details">

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
              Status
            </span>

            <strong>
              {formatLabel(
                ticket.status
              )}
            </strong>
          </div>


          <div>
            <span>
              Created
            </span>

            <strong>
              {formatDate(
                ticket.created_at
              )}
            </strong>
          </div>


          <div>
            <span>
              Last updated
            </span>

            <strong>
              {formatDate(
                ticket.updated_at
              )}
            </strong>
          </div>

        </div>


        {ticket.monday_item_id && (
          <div className="customer-case-sync">

            <span className="customer-case-sync-icon">
              ✓
            </span>

            <div>

              <strong>
                Request synchronized
              </strong>

              <span>
                Your request has been transferred
                to the support workflow.
              </span>

            </div>

          </div>
        )}


        {ticket.failure_reason && (
          <div className="alert alert-error customer-case-alert">

            <div>

              <strong>
                Case processing issue
              </strong>

              <span>
                {ticket.failure_reason}
              </span>

            </div>

          </div>
        )}


        <div className="customer-case-footer">

          <div>

            <span>
              Ticket ID
            </span>

            <code>
              {ticket.id}
            </code>

          </div>


          <button
            type="button"
            className="ticket-conversation-button"
            onClick={() =>
              toggleCaseConversation(
                ticket.id
              )
            }
          >
            {conversationOpen
              ? "Hide conversation"
              : "💬 View conversation"}
          </button>

        </div>


        {conversationOpen && (
          <div className="ticket-conversation-panel customer-conversation-panel">

            <div className="ticket-conversation-header">

              <div>

                <h4>
                  Case Conversation
                </h4>

                <p>
                  Messages between you and Harbor support.
                </p>

              </div>


              <button
                type="button"
                className="conversation-refresh-button"
                onClick={() =>
                  loadCaseUpdates(
                    ticket.id
                  )
                }
                aria-label="Refresh conversation"
              >
                ↻
              </button>

            </div>


            {caseUpdatesLoading
              ? (
                <div className="conversation-loading">
                  Loading conversation...
                </div>
              )
              : caseUpdates.length === 0
                ? (
                  <div className="conversation-empty">
                    No replies yet.
                  </div>
                )
                : (
                  <div className="ticket-update-list">

                    {caseUpdates.map(
                      (update) => {

                        const fromCustomer =
                          update.update_type
                          === "customer_reply";


                        return (
                          <div
                            key={
                              update.id
                            }
                            className={
                              fromCustomer
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
                                {fromCustomer
                                  ? "You"
                                  : "Harbor Support"}
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

                          </div>
                        );
                      }
                    )}

                  </div>
                )}


            {caseConversationError && (
              <div className="conversation-error">
                {caseConversationError}
              </div>
            )}


            <form
              className="ticket-update-composer"
              onSubmit={(event) =>
                submitCaseReply(
                  event,
                  ticket.id
                )
              }
            >

              <textarea
                rows="3"
                value={
                  caseReply
                }
                onChange={(event) =>
                  setCaseReply(
                    event.target.value
                  )
                }
                placeholder="Write a reply to Harbor support..."
                disabled={
                  caseReplySubmitting
                }
              />


              <div className="ticket-update-composer-footer">

                <span>
                  Your reply will be visible to Harbor support.
                </span>


                <button
                  type="submit"
                  className="reply-submit"
                  disabled={
                    caseReplySubmitting
                    || !caseReply.trim()
                  }
                >
                  {caseReplySubmitting
                    ? "Sending..."
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
     PAGE
     ======================================================= */

  return (
    <div className="app-page">

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
                AI Support
              </span>

            </div>

          </div>


          <div className="topbar-center">

            <span className="live-indicator">

              <span className="status-dot" />

              {activeView === "chat"
                ? "AI Assistant Online"
                : "Customer Support Cases"}

            </span>

          </div>


          <div className="topbar-actions">

            <div className="user-chip">

              <div className="avatar">
                {user?.email
                  ?.charAt(0)
                  ?.toUpperCase()
                  || "U"}
              </div>

              <div className="user-chip-copy">

                <strong>
                  {user?.email}
                </strong>

                <span>
                  Customer
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


      <main className="chat-page">

        <section className="chat-hero">

          <div>

            <span className="eyebrow">
              HARBOR SUPPORT
            </span>

            <h1>
              {activeView === "chat"
                ? "How can we help?"
                : "My Cases"}
            </h1>

            <p>
              {activeView === "chat"
                ? (
                  "Ask questions about your account, "
                  + "service, policies, or support documentation."
                )
                : (
                  "Track your support requests and "
                  + "communicate with Harbor support."
                )}
            </p>

          </div>


          {activeView === "chat" && (
            <div className="chat-hero-meta">

              <div className="hero-meta-item">

                <span className="meta-icon">
                  ✓
                </span>

                Grounded answers

              </div>


              <div className="hero-meta-item">

                <span className="meta-icon">
                  ↗
                </span>

                Human escalation

              </div>

            </div>
          )}

        </section>


        <div className="customer-view-tabs">

          <button
            type="button"
            className={
              activeView === "chat"
                ? (
                  "customer-view-tab "
                  + "customer-view-tab-active"
                )
                : "customer-view-tab"
            }
            onClick={() =>
              setActiveView(
                "chat"
              )
            }
          >
            ✦ AI Support
          </button>


          <button
            type="button"
            className={
              activeView === "cases"
                ? (
                  "customer-view-tab "
                  + "customer-view-tab-active"
                )
                : "customer-view-tab"
            }
            onClick={
              openCases
            }
          >
            ◫ My Cases

            {cases.length > 0 && (
              <span className="customer-tab-count">
                {cases.length}
              </span>
            )}
          </button>

        </div>


        {/* =================================================
            AI CHAT
            ================================================= */}

        {activeView === "chat" && (
          <section className="chat-workspace glass-card">

            <div className="chat-workspace-header">

              <div className="assistant-heading">

                <div className="assistant-avatar">
                  H
                </div>

                <div>

                  <h2>
                    Harbor AI Assistant
                  </h2>

                  <p>
                    Secure, grounded support powered by your knowledge base.
                  </p>

                </div>

              </div>


              <span className="badge badge-success">
                Online
              </span>

            </div>


            <div className="chat-thread">

              {messages.length === 0 && (
                <div className="empty-chat">

                  <div className="empty-chat-icon">
                    ✦
                  </div>

                  <h3>
                    Start a conversation
                  </h3>

                  <p>
                    Harbor can answer support questions,
                    remember context, cite sources, and
                    escalate to a human when needed.
                  </p>


                  <div className="suggestion-grid">

                    <button
                      type="button"
                      className="suggestion-card"
                      onClick={() =>
                        setInput(
                          "What is your refund policy?"
                        )
                      }
                    >
                      <span>
                        ↳
                      </span>

                      <div>

                        <strong>
                          Refund policy
                        </strong>

                        <small>
                          Ask about support policies
                        </small>

                      </div>
                    </button>


                    <button
                      type="button"
                      className="suggestion-card"
                      onClick={() =>
                        setInput(
                          "I need help with my account."
                        )
                      }
                    >
                      <span>
                        ?
                      </span>

                      <div>

                        <strong>
                          Account support
                        </strong>

                        <small>
                          Get guided assistance
                        </small>

                      </div>
                    </button>


                    <button
                      type="button"
                      className="suggestion-card"
                      onClick={() =>
                        setInput(
                          "I want to speak with a human support agent."
                        )
                      }
                    >
                      <span>
                        ↗
                      </span>

                      <div>

                        <strong>
                          Human support
                        </strong>

                        <small>
                          Request escalation
                        </small>

                      </div>
                    </button>

                  </div>

                </div>
              )}


              {messages.map(
                (message) => (
                  <div
                    key={
                      message.id
                    }
                    className={
                      message.role === "user"
                        ? "message-row message-row-user"
                        : "message-row message-row-assistant"
                    }
                  >

                    {message.role
                      === "assistant"
                      && (
                        <div className="message-avatar assistant-message-avatar">
                          H
                        </div>
                      )}


                    <div
                      className={
                        message.role === "user"
                          ? "message-bubble user-bubble"
                          : "message-bubble assistant-bubble"
                      }
                    >

                      <div className="message-meta">

                        <strong>
                          {message.role === "user"
                            ? "You"
                            : "Harbor"}
                        </strong>

                        {message.role
                          === "assistant"
                          && (
                            <span>
                              {message.streaming
                                ? "Responding..."
                                : "AI Assistant"}
                            </span>
                          )}

                      </div>


                      {message.role === "assistant"
                        && message.streaming
                        && !message.content
                        ? (
                          <div className="typing-dots">
                            <span />
                            <span />
                            <span />
                          </div>
                        )
                        : (
                          <p className="message-content">
                            {message.content}
                          </p>
                        )}


                      {message.role
                        === "assistant"
                        && !message.streaming
                        && (
                          <>

                            <div className="message-tags">

                              {message.action && (
                                <span className="badge">
                                  {formatLabel(
                                    message.action
                                  )}
                                </span>
                              )}


                              {message.severity && (
                                <span
                                  className={
                                    getSeverityClass(
                                      message.severity
                                    )
                                  }
                                >
                                  {formatLabel(
                                    message.severity
                                  )}
                                </span>
                              )}

                            </div>


                            {message.escalationRequired && (
                              <div className="escalation-card">

                                <div className="escalation-card-header">

                                  <div className="escalation-icon">
                                    !
                                  </div>

                                  <div>

                                    <strong>
                                      Human support required
                                    </strong>

                                    <p>
                                      Harbor identified that this request
                                      requires support-agent review.
                                    </p>

                                  </div>

                                </div>


                                {message.ticketId
                                  ? (
                                    <div className="ticket-detail-grid">

                                      <div>

                                        <span>
                                          Ticket ID
                                        </span>

                                        <strong className="ticket-id">
                                          {String(
                                            message.ticketId
                                          ).slice(
                                            0,
                                            12
                                          )}
                                        </strong>

                                      </div>


                                      <div>

                                        <span>
                                          Status
                                        </span>

                                        <strong>
                                          {formatLabel(
                                            message.ticketStatus
                                          )}
                                        </strong>

                                      </div>


                                      <div>

                                        <span>
                                          Approval
                                        </span>

                                        <strong>
                                          {formatLabel(
                                            message.approvalStatus
                                          )}
                                        </strong>

                                      </div>

                                    </div>
                                  )
                                  : (
                                    <div className="ticket-confirmation-note">
                                      No support ticket has been created yet.
                                    </div>
                                  )}

                              </div>
                            )}


                            {message.citations
                              ?.length > 0
                              && (
                                <div className="citation-panel">

                                  <div className="citation-heading">
                                    ◫ Sources
                                  </div>

                                  <div className="citation-list">

                                    {message.citations.map(
                                      (
                                        citation,
                                        citationIndex
                                      ) => (
                                        <div
                                          className="citation-chip"
                                          key={
                                            citationIndex
                                          }
                                        >

                                          <strong>
                                            {citation.source}
                                          </strong>

                                          {citation.chunk_index
                                            !== undefined
                                            && (
                                              <span>
                                                Chunk{" "}
                                                {citation.chunk_index}
                                              </span>
                                            )}

                                        </div>
                                      )
                                    )}

                                  </div>

                                </div>
                              )}

                          </>
                        )}

                    </div>


                    {message.role
                      === "user"
                      && (
                        <div className="message-avatar user-message-avatar">
                          {user?.email
                            ?.charAt(0)
                            ?.toUpperCase()
                            || "U"}
                        </div>
                      )}

                  </div>
                )
              )}


              <div
                ref={
                  messagesEndRef
                }
              />

            </div>


            {error && (
              <div className="alert alert-error chat-error">

                <div>

                  <strong>
                    Request failed
                  </strong>

                  <span>
                    {error}
                  </span>

                </div>

              </div>
            )}


            <div className="chat-composer-shell">

              <form
                className="chat-composer"
                onSubmit={
                  sendMessage
                }
              >

                <textarea
                  rows="1"
                  value={
                    input
                  }
                  onChange={(event) =>
                    setInput(
                      event.target.value
                    )
                  }
                  onKeyDown={
                    handleKeyDown
                  }
                  placeholder="Ask Harbor anything..."
                  disabled={
                    sending
                  }
                />


                <button
                  type="submit"
                  className="send-button"
                  disabled={
                    sending
                    || !input.trim()
                  }
                >
                  {sending
                    ? (
                      <span className="button-spinner" />
                    )
                    : "↑"}
                </button>

              </form>


              <div className="composer-footer">

                <span>
                  Press Enter to send ·
                  Shift + Enter for a new line
                </span>


                {conversationId && (
                  <span className="conversation-pill">
                    Conversation active
                  </span>
                )}

              </div>

            </div>

          </section>
        )}


        {/* =================================================
            MY CASES
            ================================================= */}

        {activeView === "cases" && (
          <section className="cases-workspace glass-card">

            <div className="cases-header">

              <div>

                <h2>
                  Support Cases
                </h2>

                <p>
                  Track cases and communicate with Harbor support.
                </p>

              </div>


              <button
                type="button"
                className="secondary-button"
                onClick={() =>
                  loadCases(
                    true
                  )
                }
                disabled={
                  casesRefreshing
                }
              >
                {casesRefreshing
                  ? "Refreshing..."
                  : "↻ Refresh"}
              </button>

            </div>


            {casesError && (
              <div className="alert alert-error">

                <div>

                  <strong>
                    Could not load cases
                  </strong>

                  <span>
                    {casesError}
                  </span>

                </div>

              </div>
            )}


            {casesLoading
              ? (
                <div className="cases-loading">

                  <div className="loader-spinner" />

                  Loading your cases...

                </div>
              )
              : cases.length === 0
                ? (
                  <div className="cases-empty">

                    <div className="cases-empty-icon">
                      ✓
                    </div>

                    <h3>
                      No support cases yet
                    </h3>

                    <p>
                      Confirmed human-support requests
                      will appear here.
                    </p>

                  </div>
                )
                : (
                  <>

                    <div className="case-status-tabs">

                      {[
                        [
                          "pending",
                          "Pending",
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
                          "Rejected",
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
                              activeCaseTab === key
                                ? (
                                  "case-status-tab "
                                  + "case-status-tab-active"
                                )
                                : "case-status-tab"
                            }
                            onClick={() => {
                              setActiveCaseTab(
                                key
                              );

                              setExpandedCaseId(
                                null
                              );
                            }}
                          >

                            {label}

                            <span className="case-status-count">
                              {
                                caseGroups[
                                  key
                                ].length
                              }
                            </span>

                          </button>
                        )
                      )}

                    </div>


                    <section className="customer-case-tab-panel">

                      <div className="customer-case-tab-header">

                        <div>

                          <h3>
                            {
                              caseTabConfig[
                                activeCaseTab
                              ].title
                            }
                          </h3>

                          <p>
                            {
                              caseTabConfig[
                                activeCaseTab
                              ].description
                            }
                          </p>

                        </div>


                        <span className="customer-case-panel-count">
                          {activeCaseGroup.length}
                          {" "}
                          {activeCaseGroup.length === 1
                            ? "case"
                            : "cases"}
                        </span>

                      </div>


                      {activeCaseGroup.length === 0
                        ? (
                          <div className="customer-case-tab-empty">

                            <div className="customer-case-tab-empty-icon">
                              ✓
                            </div>

                            <h3>
                              Nothing here
                            </h3>

                            <p>
                              You currently have no
                              cases in this stage.
                            </p>

                          </div>
                        )
                        : (
                          <div className="customer-case-list">

                            {activeCaseGroup.map(
                              renderCaseCard
                            )}

                          </div>
                        )}

                    </section>

                  </>
                )}

          </section>
        )}

      </main>

    </div>
  );
}
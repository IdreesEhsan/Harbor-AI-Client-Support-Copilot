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
  getConversation,
  getConversations,
} from "../api/conversations";

import {
  getMyCaseUpdates,
  getMyCases,
  replyToMyCase,
} from "../api/tickets";

import {
  useAuth,
} from "../context/AuthContext";

import {
  connectNotificationSocket,
} from "../realtime/notifications";

import RagFeedback from "../components/RagFeedback";

import "../styles/conversation-sidebar.css";
import "../styles/notifications.css";


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
     AI CHAT
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

  const [
    openingConversationId,
    setOpeningConversationId,
  ] = useState(null);

  const messagesEndRef =
    useRef(null);


  /* =======================================================
     AI CONVERSATION SIDEBAR
     ======================================================= */

  const [
    conversations,
    setConversations,
  ] = useState([]);

  const [
    historyLoading,
    setHistoryLoading,
  ] = useState(true);

  const [
    historyRefreshing,
    setHistoryRefreshing,
  ] = useState(false);

  const [
    historyError,
    setHistoryError,
  ] = useState("");

  const [
    conversationSearch,
    setConversationSearch,
  ] = useState("");


  /* =======================================================
     MY CASES
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
     REALTIME NOTIFICATIONS
     ======================================================= */

  const [
    messageNotifications,
    setMessageNotifications,
  ] = useState([]);

  const [
    notificationMenuOpen,
    setNotificationMenuOpen,
  ] = useState(false);

  const [
    unreadByCase,
    setUnreadByCase,
  ] = useState({});

  const expandedCaseIdRef =
    useRef(null);

  const notificationMenuRef =
    useRef(null);


  /* =======================================================
     HELPERS
     ======================================================= */

  const createLocalId = () => {
    if (
      typeof crypto
      !== "undefined"
      && crypto.randomUUID
    ) {
      return crypto.randomUUID();
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

    const minute =
      60 * 1000;

    const hour =
      60 * minute;

    const day =
      24 * hour;


    if (
      difference
      < minute
    ) {
      return "Now";
    }


    if (
      difference
      < hour
    ) {
      return (
        `${Math.floor(
          difference
          / minute
        )}m`
      );
    }


    if (
      difference
      < day
    ) {
      return (
        `${Math.floor(
          difference
          / hour
        )}h`
      );
    }


    if (
      difference
      < day * 7
    ) {
      return (
        `${Math.floor(
          difference
          / day
        )}d`
      );
    }


    return date.toLocaleDateString(
      undefined,
      {
        month:
          "short",

        day:
          "numeric",
      }
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


  /* =======================================================
     FEEDBACK QUESTION LOOKUP
     ======================================================= */

  const getPreviousUserQuestion = (
    messageIndex
  ) => {
    for (
      let index =
        messageIndex - 1;

      index >= 0;

      index -= 1
    ) {
      const previousMessage =
        messages[
          index
        ];


      if (
        previousMessage?.role
        === "user"
      ) {
        return (
          previousMessage.content
          || ""
        );
      }
    }


    return "";
  };


  /* =======================================================
     KEEP EXPANDED CASE REF CURRENT
     ======================================================= */

  useEffect(() => {
    expandedCaseIdRef.current =
      expandedCaseId;
  }, [
    expandedCaseId,
  ]);


  /* =======================================================
     CLOSE NOTIFICATION DROPDOWN ON OUTSIDE CLICK
     ======================================================= */

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


  /* =======================================================
     REALTIME CUSTOMER WEBSOCKET
     ======================================================= */

  useEffect(() => {
    if (
      !user
      || user.role !== "customer"
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
              !== "customer"
              || notification?.update_type
              !== "staff_reply"
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
                const alreadyExists =
                  current.some(
                    (item) =>
                      item.id
                      === notification.id
                  );


                if (alreadyExists) {
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
              expandedCaseIdRef.current
              === ticketId
            ) {
              setCaseUpdates(
                (current) => {
                  const alreadyExists =
                    current.some(
                      (update) =>
                        update.id
                        === notification.id
                    );


                  if (alreadyExists) {
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


            setUnreadByCase(
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


            setCasesLoaded(
              false
            );
          },


        onReady:
          () => {
            console.log(
              "Harbor customer realtime ready."
            );
          },


        onError:
          (
            event
          ) => {
            console.error(
              "Harbor customer realtime error:",
              event
            );
          },
      });


    return disconnect;

  }, [
    user,
  ]);


  /* =======================================================
     AI AUTO SCROLL
     ======================================================= */

  useEffect(() => {
    if (
      activeView !== "chat"
    ) {
      return;
    }


    messagesEndRef
      .current
      ?.scrollIntoView({
        behavior:
          "smooth",
      });

  }, [
    messages,
    sending,
    activeView,
  ]);


  /* =======================================================
     LOAD AI CONVERSATION HISTORY
     ======================================================= */

  const loadConversationHistory =
    useCallback(
      async (
        refresh = false
      ) => {
        setHistoryError("");


        if (refresh) {
          setHistoryRefreshing(
            true
          );
        } else {
          setHistoryLoading(
            true
          );
        }


        try {
          const data =
            await getConversations();


          setConversations(
            Array.isArray(
              data
            )
              ? data
              : []
          );

        } catch (err) {
          console.error(
            "Unable to load conversation history:",
            err
          );


          setHistoryError(
            err.response
              ?.data
              ?.detail
            || (
              "Unable to load "
              + "conversation history."
            )
          );

        } finally {
          setHistoryLoading(
            false
          );

          setHistoryRefreshing(
            false
          );
        }
      },
      []
    );


  useEffect(() => {
    loadConversationHistory();
  }, [
    loadConversationHistory,
  ]);


  /* =======================================================
     FILTER SIDEBAR CONVERSATIONS
     ======================================================= */

  const filteredConversations =
    useMemo(
      () => {
        const query =
          conversationSearch
            .trim()
            .toLowerCase();


        if (!query) {
          return conversations;
        }


        return conversations.filter(
          (conversation) => {
            const title =
              String(
                conversation.title
                || ""
              ).toLowerCase();

            const preview =
              String(
                conversation.preview
                || ""
              ).toLowerCase();


            return (
              title.includes(
                query
              )
              || preview.includes(
                query
              )
            );
          }
        );
      },
      [
        conversations,
        conversationSearch,
      ]
    );


  const recentConversation =
    conversations.length > 0
      ? conversations[0]
      : null;


  /* =======================================================
     OPEN EXISTING AI CONVERSATION
     ======================================================= */

  const openConversation =
    async (
      selectedConversationId
    ) => {
      if (
        selectedConversationId
        === conversationId
      ) {
        setActiveView(
          "chat"
        );

        return;
      }


      if (
        sending
        || openingConversationId
      ) {
        return;
      }


      setOpeningConversationId(
        selectedConversationId
      );

      setError("");

      setActiveView(
        "chat"
      );


      try {
        const data =
          await getConversation(
            selectedConversationId
          );


        const loadedMessages =
          (
            data.messages
            || []
          )
            .filter(
              (message) =>
                message.role === "user"
                || message.role === "assistant"
            )
            .map(
              (message) => {
                const metadata =
                  message.metadata
                  || {};


                return {
                  id:
                    message.id
                    || createLocalId(),

                  role:
                    message.role,

                  content:
                    message.content,

                  streaming:
                    false,

                  action:
                    metadata.action
                    ?? null,

                  severity:
                    metadata.severity
                    ?? null,

                  citations:
                    metadata.citations
                    ?? [],

                  escalationRequired:
                    metadata
                      .escalation_required
                    ?? false,

                  ticketId:
                    metadata.ticket_id
                    ?? null,

                  ticketStatus:
                    metadata.ticket_status
                    ?? null,

                  approvalStatus:
                    metadata.approval_status
                    ?? null,
                };
              }
            );


        setMessages(
          loadedMessages
        );

        setConversationId(
          selectedConversationId
        );

        setInput("");

      } catch (err) {
        console.error(
          "Unable to open conversation:",
          err
        );


        setError(
          err.response
            ?.data
            ?.detail
          || (
            "Unable to open "
            + "this conversation."
          )
        );

      } finally {
        setOpeningConversationId(
          null
        );
      }
    };


  /* =======================================================
     NEW CHAT
     ======================================================= */

  const startNewConversation =
    () => {
      if (sending) {
        return;
      }


      setConversationId("");

      setMessages([]);

      setInput("");

      setError("");

      setActiveView(
        "chat"
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
              [
                "approved",
                "executing",
              ].includes(
                ticket.status
              )
          ),

        successful:
          cases.filter(
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
          cases.filter(
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
        cases,
      ]
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
        (
          "Support requests waiting for "
          + "a Harbor support agent to review."
        ),
    },

    approved: {
      title:
        "Approved",

      description:
        (
          "Support requests approved "
          + "and waiting for processing."
        ),
    },

    successful: {
      title:
        "Successful / Processed",

      description:
        (
          "Support requests successfully "
          + "processed or currently progressing."
        ),
    },

    rejected: {
      title:
        "Rejected / Failed",

      description:
        (
          "Support requests that were rejected "
          + "or could not be completed."
        ),
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
            err.response
              ?.data
              ?.detail
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
     CASE UPDATES
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
          err.response
            ?.data
            ?.detail
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


  /* =======================================================
     MARK CASE READ
     ======================================================= */

  const markCaseRead =
    (
      ticketId
    ) => {
      setUnreadByCase(
        (current) => ({
          ...current,

          [ticketId]:
            0,
        })
      );
    };


  /* =======================================================
     TOGGLE CASE CONVERSATION
     ======================================================= */

  const toggleCaseConversation =
    async (
      ticketId
    ) => {
      markCaseRead(
        ticketId
      );


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
     CUSTOMER REPLY
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
          err.response
            ?.data
            ?.detail
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
     NOTIFICATION HELPERS
     ======================================================= */

  const getCaseTabForStatus =
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


  const openCaseFromNotification =
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


      markCaseRead(
        ticketId
      );


      setActiveView(
        "cases"
      );


      setActiveCaseTab(
        getCaseTabForStatus(
          notification.ticket
            ?.status
        )
      );


      setExpandedCaseId(
        ticketId
      );


      setCaseReply("");

      setCaseConversationError("");


      await Promise.all([
        loadCases(
          true
        ),

        loadCaseUpdates(
          ticketId
        ),
      ]);
    };


  const totalUnreadNotifications =
    useMemo(
      () =>
        Object.values(
          unreadByCase
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
        unreadByCase,
      ]
    );


  /* =======================================================
     SEND AI MESSAGE
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
              (
                token
              ) => {
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
                    data
                      .escalation_required
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


        await loadConversationHistory(
          true
        );


        window.setTimeout(
          () => {
            loadConversationHistory(
              true
            );
          },
          1200
        );


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


  /* =======================================================
     ENTER TO SEND
     ======================================================= */

  const handleKeyDown =
    (
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
     QUICK PROMPT
     ======================================================= */

  const useQuickPrompt =
    (
      prompt
    ) => {
      setInput(
        prompt
      );
    };


  /* =======================================================
     CASE CARD
     ======================================================= */

  const renderCaseCard =
    (
      ticket
    ) => {
      const conversationOpen =
        expandedCaseId
        === ticket.id;

      const unreadCount =
        unreadByCase[
          ticket.id
        ]
        || 0;


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
              className="ticket-conversation-button ticket-conversation-button-unread"
              onClick={() =>
                toggleCaseConversation(
                  ticket.id
                )
              }
            >

              <span>
                {conversationOpen
                  ? "Hide conversation"
                  : "💬 View conversation"}
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
                        (
                          update
                        ) => {
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


      {/* =================================================
          TOPBAR
          ================================================= */}

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
                <span className="notification-bell-icon">
                  🔔
                </span>


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
                        Harbor support replies
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
                            New support replies
                            will appear here.
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
                              unreadByCase[
                                ticketId
                              ]
                              || 0
                            ) > 0;


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
                                openCaseFromNotification(
                                  notification
                                )
                              }
                            >

                              <div className="notification-dropdown-avatar notification-dropdown-avatar-support">
                                H
                              </div>


                              <div className="notification-dropdown-copy">

                                <div className="notification-dropdown-title">

                                  <strong>
                                    Harbor Support
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
                                      || "Support Case"}
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


      {/* =================================================
          MAIN
          ================================================= */}

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
            AI SUPPORT
            ================================================= */}

        {activeView === "chat" && (
          <section className="harbor-ai-layout glass-card">

            <aside className="conversation-sidebar">

              <button
                type="button"
                className="sidebar-new-chat"
                onClick={
                  startNewConversation
                }
                disabled={
                  sending
                }
              >

                <span className="sidebar-new-chat-plus">
                  ＋
                </span>

                New chat

              </button>


              <div className="sidebar-search-shell">

                <span className="sidebar-search-icon">
                  ⌕
                </span>


                <input
                  type="text"
                  value={
                    conversationSearch
                  }
                  onChange={(event) =>
                    setConversationSearch(
                      event.target.value
                    )
                  }
                  placeholder="Search chats"
                />

              </div>


              <div className="sidebar-heading-row">

                <span>
                  Recent conversations
                </span>


                <button
                  type="button"
                  className="sidebar-refresh"
                  disabled={
                    historyRefreshing
                  }
                  onClick={() =>
                    loadConversationHistory(
                      true
                    )
                  }
                  aria-label="Refresh conversations"
                >
                  {historyRefreshing
                    ? "…"
                    : "↻"}
                </button>

              </div>


              <div className="sidebar-conversation-scroll">

                {historyError && (
                  <div className="sidebar-history-error">
                    {historyError}
                  </div>
                )}


                {historyLoading
                  ? (
                    <div className="sidebar-history-loading">

                      <div className="sidebar-history-skeleton" />
                      <div className="sidebar-history-skeleton" />
                      <div className="sidebar-history-skeleton" />
                      <div className="sidebar-history-skeleton" />

                    </div>
                  )

                  : filteredConversations.length === 0
                    ? (
                      <div className="sidebar-history-empty">

                        <div className="sidebar-empty-icon">
                          ✦
                        </div>


                        <strong>
                          {conversationSearch
                            ? "No matching chats"
                            : "No conversations yet"}
                        </strong>


                        <span>
                          {conversationSearch
                            ? "Try another search."
                            : (
                              "Start a new chat and your "
                              + "history will appear here."
                            )}
                        </span>

                      </div>
                    )

                    : (
                      <div className="sidebar-conversation-list">

                        {filteredConversations.map(
                          (
                            conversation
                          ) => (
                            <button
                              key={
                                conversation.id
                              }
                              type="button"
                              className={
                                conversation.id
                                === conversationId
                                  ? (
                                    "sidebar-conversation-item "
                                    + "sidebar-conversation-item-active"
                                  )
                                  : "sidebar-conversation-item"
                              }
                              disabled={
                                openingConversationId
                                === conversation.id
                              }
                              onClick={() =>
                                openConversation(
                                  conversation.id
                                )
                              }
                            >

                              <div className="sidebar-conversation-top">

                                <span className="sidebar-conversation-title">

                                  {conversation.title
                                    || "New Support Conversation"}

                                </span>


                                <span className="sidebar-conversation-time">

                                  {formatRelativeTime(
                                    conversation.updated_at
                                    || conversation.created_at
                                  )}

                                </span>

                              </div>


                              <span className="sidebar-conversation-preview">

                                {conversation.preview
                                  || "Open conversation"}

                              </span>

                            </button>
                          )
                        )}

                      </div>
                    )}

              </div>


              <div className="sidebar-footer">

                <div className="sidebar-footer-icon">
                  H
                </div>


                <div>

                  <strong>
                    Harbor AI
                  </strong>

                  <span>
                    Conversations saved securely
                  </span>

                </div>

              </div>

            </aside>


            <div className="sidebar-chat-area">

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
                      Secure support powered by
                      your knowledge base.
                    </p>

                  </div>

                </div>


                <div className="assistant-header-status">

                  {conversationId && (
                    <span className="active-chat-indicator">
                      Active conversation
                    </span>
                  )}


                  <span className="badge badge-success">
                    Online
                  </span>

                </div>

              </div>


              {openingConversationId
                ? (
                  <div className="sidebar-chat-loading">

                    <div className="loader-spinner" />

                    <strong>
                      Opening conversation
                    </strong>

                    <span>
                      Loading messages and sources...
                    </span>

                  </div>
                )

                : (
                  <>

                    {/* =====================================
                        WELCOME
                        ===================================== */}

                    {messages.length === 0 && (
                      <div className="harbor-welcome-dashboard">

                        <div className="welcome-main">

                          <div className="welcome-ai-mark">
                            ✦
                          </div>


                          <span className="welcome-eyebrow">
                            HARBOR AI COPILOT
                          </span>


                          <h2>
                            What can I help you with today?
                          </h2>


                          <p>
                            Get grounded answers, continue previous
                            conversations, or request human support
                            when you need it.
                          </p>

                        </div>


                        <div className="welcome-quick-grid">

                          <button
                            type="button"
                            className="welcome-quick-card"
                            onClick={() =>
                              useQuickPrompt(
                                "What is your refund policy?"
                              )
                            }
                          >

                            <div className="welcome-quick-icon">
                              ↳
                            </div>


                            <div>

                              <strong>
                                Refund policy
                              </strong>

                              <span>
                                Understand refunds,
                                eligibility and timelines
                              </span>

                            </div>


                            <span className="welcome-card-arrow">
                              →
                            </span>

                          </button>


                          <button
                            type="button"
                            className="welcome-quick-card"
                            onClick={() =>
                              useQuickPrompt(
                                "I need help with my account."
                              )
                            }
                          >

                            <div className="welcome-quick-icon">
                              ◉
                            </div>


                            <div>

                              <strong>
                                Account support
                              </strong>

                              <span>
                                Get guided help with
                                your Harbor account
                              </span>

                            </div>


                            <span className="welcome-card-arrow">
                              →
                            </span>

                          </button>


                          <button
                            type="button"
                            className="welcome-quick-card"
                            onClick={() =>
                              useQuickPrompt(
                                "I was charged twice and need help."
                              )
                            }
                          >

                            <div className="welcome-quick-icon">
                              $
                            </div>


                            <div>

                              <strong>
                                Billing issue
                              </strong>

                              <span>
                                Get help with charges
                                and payment problems
                              </span>

                            </div>


                            <span className="welcome-card-arrow">
                              →
                            </span>

                          </button>


                          <button
                            type="button"
                            className="welcome-quick-card"
                            onClick={() =>
                              useQuickPrompt(
                                "I want to speak with a human support agent."
                              )
                            }
                          >

                            <div className="welcome-quick-icon">
                              ↗
                            </div>


                            <div>

                              <strong>
                                Human support
                              </strong>

                              <span>
                                Escalate a request
                                to the Harbor team
                              </span>

                            </div>


                            <span className="welcome-card-arrow">
                              →
                            </span>

                          </button>

                        </div>


                        <div className="welcome-lower-grid">

                          <section className="welcome-capabilities">

                            <div className="welcome-section-heading">
                              <span>
                                Harbor capabilities
                              </span>
                            </div>


                            <div className="capability-grid">

                              <div className="capability-item">

                                <span className="capability-icon">
                                  ✓
                                </span>

                                <div>

                                  <strong>
                                    Grounded answers
                                  </strong>

                                  <span>
                                    Responses backed by your
                                    support knowledge base.
                                  </span>

                                </div>

                              </div>


                              <div className="capability-item">

                                <span className="capability-icon">
                                  ◫
                                </span>

                                <div>

                                  <strong>
                                    Source citations
                                  </strong>

                                  <span>
                                    Sources stay available
                                    when you reopen chats.
                                  </span>

                                </div>

                              </div>


                              <div className="capability-item">

                                <span className="capability-icon">
                                  ◷
                                </span>

                                <div>

                                  <strong>
                                    Conversation memory
                                  </strong>

                                  <span>
                                    Continue earlier conversations
                                    without losing context.
                                  </span>

                                </div>

                              </div>


                              <div className="capability-item">

                                <span className="capability-icon">
                                  ↗
                                </span>

                                <div>

                                  <strong>
                                    Human escalation
                                  </strong>

                                  <span>
                                    Create a support case after
                                    explicit confirmation.
                                  </span>

                                </div>

                              </div>

                            </div>

                          </section>


                          <section className="welcome-recent-panel">

                            <div className="welcome-section-heading">
                              <span>
                                Continue where you left off
                              </span>
                            </div>


                            {recentConversation
                              ? (
                                <button
                                  type="button"
                                  className="recent-conversation-card"
                                  onClick={() =>
                                    openConversation(
                                      recentConversation.id
                                    )
                                  }
                                >

                                  <div className="recent-conversation-icon">
                                    ✦
                                  </div>


                                  <div className="recent-conversation-copy">

                                    <strong>
                                      {recentConversation.title
                                        || "Recent conversation"}
                                    </strong>


                                    <span>
                                      {recentConversation.preview
                                        || "Continue this conversation"}
                                    </span>

                                  </div>


                                  <div className="recent-conversation-meta">

                                    <span>
                                      {formatRelativeTime(
                                        recentConversation.updated_at
                                        || recentConversation.created_at
                                      )}
                                    </span>

                                    <strong>
                                      →
                                    </strong>

                                  </div>

                                </button>
                              )

                              : (
                                <div className="no-recent-conversation">

                                  <div>
                                    ✦
                                  </div>

                                  <strong>
                                    Your first conversation starts here
                                  </strong>

                                  <span>
                                    Choose a suggestion above
                                    or type your own question.
                                  </span>

                                </div>
                              )}

                          </section>

                        </div>

                      </div>
                    )}


                    {/* =====================================
                        CHAT THREAD
                        ===================================== */}

                    {messages.length > 0 && (
                      <div className="chat-thread">

                        {messages.map(
                          (
                            message,
                            messageIndex
                          ) => (
                            <div
                              key={
                                message.id
                              }
                              className={
                                message.role
                                === "user"
                                  ? (
                                    "message-row "
                                    + "message-row-user"
                                  )
                                  : (
                                    "message-row "
                                    + "message-row-assistant"
                                  )
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
                                  message.role
                                  === "user"
                                    ? (
                                      "message-bubble "
                                      + "user-bubble"
                                    )
                                    : (
                                      "message-bubble "
                                      + "assistant-bubble"
                                    )
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


                                {message.role
                                  === "assistant"
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
                                                Harbor identified that this
                                                request requires support-agent
                                                review.
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
                                                No support ticket has
                                                been created yet.
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
                                                      `${citation.source || "source"}-${citation.chunk_index ?? citationIndex}`
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
                                                          {
                                                            citation
                                                              .chunk_index
                                                          }

                                                        </span>
                                                      )}

                                                  </div>
                                                )
                                              )}

                                            </div>

                                          </div>
                                        )}


                                      {/* ===================
                                          CUSTOMER FEEDBACK
                                          =================== */}

                                      {message.action === "answer"
                                        && !message.escalationRequired
                                        && (
                                          <RagFeedback
                                            messageId={
                                              message.id
                                            }
                                            question={
                                              getPreviousUserQuestion(
                                                messageIndex
                                              )
                                            }
                                            answer={
                                              message.content
                                            }
                                            citations={
                                              message.citations
                                              || []
                                            }
                                          />
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
                    )}


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

                  </>
                )}

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
                  Track your support requests and
                  communicate with Harbor support.
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
                              activeCaseTab
                              === key
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

                              setCaseUpdates([]);
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
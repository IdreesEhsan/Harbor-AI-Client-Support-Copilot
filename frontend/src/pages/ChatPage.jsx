import { useState } from "react";

import apiClient from "../api/client";
import { useAuth } from "../context/AuthContext";


export default function ChatPage() {
  const { user, logout } = useAuth();

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] =
    useState("");

  const [sending, setSending] =
    useState(false);

  const [error, setError] =
    useState("");


  const formatLabel = (value) => {
    if (!value) {
      return "";
    }

    return String(value)
      .replaceAll("_", " ")
      .replace(/\b\w/g, (character) =>
        character.toUpperCase()
      );
  };


  const sendMessage = async (event) => {
    event.preventDefault();

    const customerMessage =
      input.trim();

    if (
      !customerMessage
      || sending
    ) {
      return;
    }

    setError("");

    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: customerMessage,
      },
    ]);

    setInput("");

    setSending(true);

    try {
      const response =
        await apiClient.post(
          "/agent/chat",
          {
            message: customerMessage,

            conversation_id:
              conversationId || null,
          }
        );

      const data = response.data;

      if (data.conversation_id) {
        setConversationId(
          data.conversation_id
        );
      }

      setMessages((current) => [
        ...current,
        {
          role: "assistant",

          content:
            data.answer,

          action:
            data.action,

          severity:
            data.severity,

          citations:
            data.citations ?? [],

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
        },
      ]);

    } catch (err) {
      console.error(
        "Harbor agent request failed:",
        err
      );

      const errorMessage =
        err.response?.data?.detail
        || (
          "Harbor could not process your "
          + "request. Please try again."
        );

      setError(
        errorMessage
      );

    } finally {
      setSending(false);
    }
  };


  return (
    <main>
      <header>
        <h1>
          Harbor Support
        </h1>

        <p>
          Signed in as{" "}
          <strong>
            {user?.email}
          </strong>
        </p>

        <button
          type="button"
          onClick={logout}
        >
          Logout
        </button>
      </header>

      <hr />

      <section>
        <h2>
          AI Support Assistant
        </h2>

        {messages.length === 0 && (
          <p>
            Ask Harbor a question about your
            service, policies, or support
            documentation.
          </p>
        )}

        {messages.map(
          (message, index) => (
            <article
              key={index}
              style={{
                border:
                  "1px solid #ddd",

                borderRadius:
                  "8px",

                padding:
                  "12px",

                marginBottom:
                  "12px",
              }}
            >
              <p>
                <strong>
                  {message.role === "user"
                    ? "You"
                    : "Harbor"}
                </strong>
              </p>

              <p>
                {message.content}
              </p>

              {message.role
                === "assistant"
                && (
                  <>
                    {message.action && (
                      <p>
                        <small>
                          Action:{" "}
                          {formatLabel(
                            message.action
                          )}
                        </small>
                      </p>
                    )}

                    {message.severity && (
                      <p>
                        <small>
                          Severity:{" "}
                          {formatLabel(
                            message.severity
                          )}
                        </small>
                      </p>
                    )}

                    {message
                      .escalationRequired
                      && (
                        <p>
                          <strong>
                            This request requires
                            human support.
                          </strong>
                        </p>
                      )}

                    {message.ticketId && (
                      <section
                        style={{
                          border:
                            "1px solid #ccc",

                          borderRadius:
                            "6px",

                          padding:
                            "10px",

                          marginTop:
                            "10px",
                        }}
                      >
                        <p>
                          <strong>
                            Support ticket created
                            successfully.
                          </strong>
                        </p>

                        <p>
                          <small>
                            Ticket ID:{" "}
                            {message.ticketId}
                          </small>
                        </p>

                        {message
                          .ticketStatus
                          && (
                            <p>
                              <small>
                                Status:{" "}
                                {formatLabel(
                                  message
                                    .ticketStatus
                                )}
                              </small>
                            </p>
                          )}

                        {message
                          .approvalStatus
                          && (
                            <p>
                              <small>
                                Approval:{" "}
                                {formatLabel(
                                  message
                                    .approvalStatus
                                )}
                              </small>
                            </p>
                          )}
                      </section>
                    )}

                    {message.citations
                      ?.length > 0
                      && (
                        <div>
                          <strong>
                            Sources
                          </strong>

                          <ul>
                            {message
                              .citations
                              .map(
                                (
                                  citation,
                                  citationIndex
                                ) => (
                                  <li
                                    key={
                                      citationIndex
                                    }
                                  >
                                    {
                                      citation
                                        .source
                                    }

                                    {citation
                                      .chunk_index
                                      !== undefined
                                      && (
                                        ` — chunk ${
                                          citation
                                            .chunk_index
                                        }`
                                      )}

                                    {citation
                                      .similarity
                                      !== undefined
                                      && (
                                        ` — similarity ${
                                          Number(
                                            citation
                                              .similarity
                                          ).toFixed(
                                            3
                                          )
                                        }`
                                      )}
                                  </li>
                                )
                              )}
                          </ul>
                        </div>
                      )}
                  </>
                )}
            </article>
          )
        )}

        {sending && (
          <p>
            Harbor is thinking...
          </p>
        )}

        {error && (
          <p>
            <strong>
              Error:
            </strong>{" "}
            {error}
          </p>
        )}
      </section>

      <hr />

      <form
        onSubmit={sendMessage}
      >
        <label
          htmlFor="message"
        >
          <strong>
            Message
          </strong>
        </label>

        <br />

        <textarea
          id="message"
          rows="4"
          value={input}
          onChange={(event) =>
            setInput(
              event.target.value
            )
          }
          placeholder="Ask Harbor for help..."
          disabled={sending}
        />

        <br />

        <button
          type="submit"
          disabled={
            sending
            || !input.trim()
          }
        >
          {sending
            ? "Sending..."
            : "Send"}
        </button>
      </form>

      {conversationId && (
        <p>
          <small>
            Conversation:{" "}
            {conversationId}
          </small>
        </p>
      )}
    </main>
  );
}
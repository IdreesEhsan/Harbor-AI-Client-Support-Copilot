import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Link,
} from "react-router-dom";

import {
  createEvaluationCase,
  getEvaluationCases,
  getEvaluationRuns,
  getKnowledgeGaps,
  getPolicyConflicts,
  getRagAnalytics,
  getRagFeedback,
  runRagEvaluation,
} from "../api/ragQuality";

import {
  useAuth,
} from "../context/AuthContext";

import "../styles/rag-quality.css";


export default function RagQualityPage() {
  const {
    user,
    logout,
  } = useAuth();


  /* =======================================================
     VIEW
     ======================================================= */

  const [
    activeTab,
    setActiveTab,
  ] = useState(
    "overview"
  );


  /* =======================================================
     DATA
     ======================================================= */

  const [
    analytics,
    setAnalytics,
  ] = useState(null);


  const [
    knowledgeGaps,
    setKnowledgeGaps,
  ] = useState([]);


  const [
    conflicts,
    setConflicts,
  ] = useState([]);


  const [
    feedback,
    setFeedback,
  ] = useState([]);


  const [
    evaluationCases,
    setEvaluationCases,
  ] = useState([]);


  const [
    evaluationRuns,
    setEvaluationRuns,
  ] = useState([]);


  const [
    latestEvaluation,
    setLatestEvaluation,
  ] = useState(null);


  /* =======================================================
     LOADING / STATUS
     ======================================================= */

  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    refreshing,
    setRefreshing,
  ] = useState(false);


  const [
    runningEvaluation,
    setRunningEvaluation,
  ] = useState(false);


  const [
    creatingCase,
    setCreatingCase,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  const [
    successMessage,
    setSuccessMessage,
  ] = useState("");


  /* =======================================================
     FEEDBACK FILTER
     ======================================================= */

  const [
    feedbackFilter,
    setFeedbackFilter,
  ] = useState("");


  /* =======================================================
     EVALUATION FORM
     ======================================================= */

  const [
    evaluationQuestion,
    setEvaluationQuestion,
  ] = useState("");


  const [
    expectedAnswer,
    setExpectedAnswer,
  ] = useState("");


  const [
    expectedSources,
    setExpectedSources,
  ] = useState("");


  const [
    expectedGrounded,
    setExpectedGrounded,
  ] = useState(true);


  const [
    requesterRole,
    setRequesterRole,
  ] = useState(
    "customer"
  );


  /* =======================================================
     HELPERS
     ======================================================= */

  const formatPercent = (
    value
  ) => {
    const number =
      Number(
        value
        || 0
      );

    return (
      `${Math.round(
        number
        * 100
      )}%`
    );
  };


  const formatDate =
    (
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


  const formatLabel =
    (
      value
    ) => {
      if (!value) {
        return "Unknown";
      }


      return (
        String(
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
              character
                .toUpperCase()
          )
      );
    };


  /* =======================================================
     LOAD ALL DATA
     ======================================================= */

  const loadDashboard =
    useCallback(
      async (
        refresh = false
      ) => {
        setError("");


        if (refresh) {
          setRefreshing(
            true
          );

        } else {
          setLoading(
            true
          );
        }


        try {
          const [
            analyticsData,
            gapsData,
            conflictsData,
            feedbackData,
            casesData,
            runsData,
          ] = await Promise.all([
            getRagAnalytics(),

            getKnowledgeGaps(
              100
            ),

            getPolicyConflicts(
              100
            ),

            getRagFeedback({
              limit:
                100,
            }),

            getEvaluationCases(
              true
            ),

            getEvaluationRuns(
              50
            ),
          ]);


          setAnalytics(
            analyticsData
            || {}
          );


          setKnowledgeGaps(
            Array.isArray(
              gapsData
            )
              ? gapsData
              : []
          );


          setConflicts(
            Array.isArray(
              conflictsData
            )
              ? conflictsData
              : []
          );


          setFeedback(
            Array.isArray(
              feedbackData
            )
              ? feedbackData
              : []
          );


          setEvaluationCases(
            Array.isArray(
              casesData
            )
              ? casesData
              : []
          );


          setEvaluationRuns(
            Array.isArray(
              runsData
            )
              ? runsData
              : []
          );

        } catch (err) {
          console.error(
            "Unable to load RAG quality dashboard:",
            err
          );


          setError(
            err.response
              ?.data
              ?.detail
            || (
              "Unable to load "
              + "RAG quality information."
            )
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
    loadDashboard();
  }, [
    loadDashboard,
  ]);


  /* =======================================================
     FEEDBACK FILTER
     ======================================================= */

  const filteredFeedback =
    useMemo(
      () => {
        if (!feedbackFilter) {
          return feedback;
        }


        return (
          feedback.filter(
            (
              item
            ) =>
              item.rating
              === feedbackFilter
          )
        );
      },
      [
        feedback,
        feedbackFilter,
      ]
    );


  /* =======================================================
     RUN EVALUATION
     ======================================================= */

  const handleRunEvaluation =
    async () => {
      setRunningEvaluation(
        true
      );

      setError("");

      setSuccessMessage("");


      try {
        const result =
          await runRagEvaluation();


        setLatestEvaluation(
          result
        );


        setSuccessMessage(
          (
            "RAG evaluation completed "
            + "successfully."
          )
        );


        const runs =
          await getEvaluationRuns(
            50
          );


        setEvaluationRuns(
          Array.isArray(
            runs
          )
            ? runs
            : []
        );

      } catch (err) {
        console.error(
          "RAG evaluation failed:",
          err
        );


        setError(
          err.response
            ?.data
            ?.detail
          || (
            "Unable to run "
            + "RAG evaluation."
          )
        );

      } finally {
        setRunningEvaluation(
          false
        );
      }
    };


  /* =======================================================
     CREATE EVALUATION CASE
     ======================================================= */

  const handleCreateCase =
    async (
      event
    ) => {
      event.preventDefault();


      const question =
        evaluationQuestion
          .trim();


      if (!question) {
        setError(
          (
            "Evaluation question "
            + "is required."
          )
        );

        return;
      }


      const answerTerms =
        expectedAnswer
          .split(",")
          .map(
            (
              value
            ) =>
              value.trim()
          )
          .filter(
            Boolean
          );


      const sources =
        expectedSources
          .split(",")
          .map(
            (
              value
            ) =>
              value.trim()
          )
          .filter(
            Boolean
          );


      setCreatingCase(
        true
      );

      setError("");

      setSuccessMessage("");


      try {
        await createEvaluationCase({
          question,

          expectedAnswerContains:
            answerTerms,

          expectedSources:
            sources,

          expectedGrounded,

          requesterRole,
        });


        setSuccessMessage(
          (
            "Evaluation test case "
            + "created successfully."
          )
        );


        setEvaluationQuestion(
          ""
        );

        setExpectedAnswer(
          ""
        );

        setExpectedSources(
          ""
        );

        setExpectedGrounded(
          true
        );

        setRequesterRole(
          "customer"
        );


        const cases =
          await getEvaluationCases(
            true
          );


        setEvaluationCases(
          Array.isArray(
            cases
          )
            ? cases
            : []
        );

      } catch (err) {
        console.error(
          "Unable to create evaluation case:",
          err
        );


        setError(
          err.response
            ?.data
            ?.detail
          || (
            "Unable to create "
            + "evaluation case."
          )
        );

      } finally {
        setCreatingCase(
          false
        );
      }
    };


  /* =======================================================
     OVERVIEW METRICS
     ======================================================= */

  const overviewMetrics = [
    {
      label:
        "Total queries",

      value:
        analytics
          ?.total_queries
        ?? 0,

      hint:
        "Recorded production RAG requests",

      type:
        "indigo",
    },

    {
      label:
        "Grounded rate",

      value:
        formatPercent(
          analytics
            ?.grounded_rate
        ),

      hint:
        "Queries answered from verified knowledge",

      type:
        "green",
    },

    {
      label:
        "Knowledge gaps",

      value:
        analytics
          ?.knowledge_gaps
        ?? 0,

      hint:
        "Questions with insufficient evidence",

      type:
        "orange",
    },

    {
      label:
        "Positive feedback",

      value:
        formatPercent(
          analytics
            ?.positive_feedback_rate
        ),

      hint:
        "Positive ratings from users",

      type:
        "blue",
    },

    {
      label:
        "Avg. chunks",

      value:
        analytics
          ?.average_retrieved_chunks
        ?? 0,

      hint:
        "Average evidence chunks per query",

      type:
        "purple",
    },
  ];


  /* =======================================================
     LOADER
     ======================================================= */

  if (loading) {
    return (
      <div className="fullscreen-loader">

        <div className="loader-logo">
          H
        </div>

        <div className="loader-spinner" />

        <p>
          Loading RAG quality...
        </p>

      </div>
    );
  }


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
                RAG Quality
              </span>

            </div>

          </div>


          <div className="rag-quality-navigation">

            <Link
              to="/staff"
              className="rag-quality-nav-link"
            >
              Operations
            </Link>


            <Link
              to="/staff/knowledge"
              className="rag-quality-nav-link"
            >
              Knowledge
            </Link>


            <Link
              to="/staff/rag-quality"
              className={
                (
                  "rag-quality-nav-link "
                  + "rag-quality-nav-link-active"
                )
              }
            >
              RAG Quality
            </Link>

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
                  {user?.role === "admin"
                    ? "Administrator"
                    : "Support Agent"}
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

      <main className="rag-quality-page">

        <section className="rag-quality-hero">

          <div>

            <span className="eyebrow">
              RAG QUALITY CONTROL
            </span>


            <h1>
              AI Quality Dashboard
            </h1>


            <p>
              Monitor retrieval quality, identify missing
              knowledge, review feedback, detect policy
              conflicts, and continuously evaluate Harbor AI.
            </p>

          </div>


          <button
            type="button"
            className="secondary-button"
            disabled={
              refreshing
            }
            onClick={() =>
              loadDashboard(
                true
              )
            }
          >
            ↻{" "}
            {refreshing
              ? "Refreshing..."
              : "Refresh"}
          </button>

        </section>


        {/* =================================================
            ALERTS
            ================================================= */}

        {error && (
          <div className="alert alert-error">

            <div>

              <strong>
                Something went wrong
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
            TABS
            ================================================= */}

        <div className="rag-quality-tabs">

          {[
            [
              "overview",
              "Overview",
            ],

            [
              "gaps",
              "Knowledge Gaps",
            ],

            [
              "conflicts",
              "Conflicts",
            ],

            [
              "feedback",
              "Feedback",
            ],

            [
              "evaluations",
              "Evaluations",
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
                      "rag-quality-tab "
                      + "rag-quality-tab-active"
                    )
                    : "rag-quality-tab"
                }
                onClick={() =>
                  setActiveTab(
                    key
                  )
                }
              >
                {label}
              </button>
            )
          )}

        </div>


        {/* =================================================
            OVERVIEW
            ================================================= */}

        {activeTab === "overview" && (
          <>

            <section className="rag-metric-grid">

              {overviewMetrics.map(
                (
                  metric
                ) => (
                  <article
                    key={
                      metric.label
                    }
                    className={
                      (
                        "rag-metric-card "
                        + `rag-metric-${metric.type}`
                      )
                    }
                  >

                    <span>
                      {metric.label}
                    </span>


                    <strong>
                      {metric.value}
                    </strong>


                    <small>
                      {metric.hint}
                    </small>

                  </article>
                )
              )}

            </section>


            <section className="rag-overview-grid">

              <article className="rag-panel">

                <div className="rag-panel-header">

                  <div>

                    <span className="eyebrow">
                      USER SIGNALS
                    </span>

                    <h2>
                      Feedback health
                    </h2>

                  </div>

                </div>


                <div className="rag-feedback-summary">

                  <div>

                    <span>
                      Total feedback
                    </span>

                    <strong>
                      {
                        analytics
                          ?.total_feedback
                        ?? 0
                      }
                    </strong>

                  </div>


                  <div>

                    <span>
                      Positive
                    </span>

                    <strong className="quality-positive">
                      {
                        analytics
                          ?.positive_feedback
                        ?? 0
                      }
                    </strong>

                  </div>


                  <div>

                    <span>
                      Negative
                    </span>

                    <strong className="quality-negative">
                      {
                        analytics
                          ?.negative_feedback
                        ?? 0
                      }
                    </strong>

                  </div>

                </div>

              </article>


              <article className="rag-panel">

                <div className="rag-panel-header">

                  <div>

                    <span className="eyebrow">
                      RISK SIGNALS
                    </span>

                    <h2>
                      Knowledge health
                    </h2>

                  </div>

                </div>


                <div className="rag-feedback-summary">

                  <div>

                    <span>
                      Knowledge gaps
                    </span>

                    <strong>
                      {knowledgeGaps.length}
                    </strong>

                  </div>


                  <div>

                    <span>
                      Conflicts
                    </span>

                    <strong className="quality-negative">
                      {conflicts.length}
                    </strong>

                  </div>


                  <div>

                    <span>
                      Eval cases
                    </span>

                    <strong>
                      {evaluationCases.length}
                    </strong>

                  </div>

                </div>

              </article>

            </section>

          </>
        )}


        {/* =================================================
            KNOWLEDGE GAPS
            ================================================= */}

        {activeTab === "gaps" && (
          <section className="rag-panel">

            <div className="rag-panel-header">

              <div>

                <span className="eyebrow">
                  MISSING KNOWLEDGE
                </span>

                <h2>
                  Knowledge Gaps
                </h2>

                <p>
                  Questions Harbor could not answer from
                  qualifying knowledge-base evidence.
                </p>

              </div>


              <span className="rag-count-pill">
                {knowledgeGaps.length}
              </span>

            </div>


            {knowledgeGaps.length === 0
              ? (
                <div className="rag-empty-state">

                  <div>
                    ✓
                  </div>

                  <h3>
                    No knowledge gaps
                  </h3>

                  <p>
                    Harbor currently has sufficient
                    knowledge for recorded requests.
                  </p>

                </div>
              )

              : (
                <div className="rag-record-list">

                  {knowledgeGaps.map(
                    (
                      gap
                    ) => (
                      <article
                        key={
                          gap.id
                        }
                        className="rag-record-card"
                      >

                        <div className="rag-record-top">

                          <div>

                            <span className="rag-record-label">
                              Customer query
                            </span>


                            <h3>
                              {gap.original_query}
                            </h3>

                          </div>


                          <span className="rag-status-warning">
                            Knowledge Gap
                          </span>

                        </div>


                        {gap.rewritten_query
                          && gap.rewritten_query
                          !== gap.original_query
                          && (
                            <div className="rag-record-field">

                              <span>
                                Rewritten query
                              </span>

                              <p>
                                {gap.rewritten_query}
                              </p>

                            </div>
                          )}


                        <div className="rag-record-meta">

                          <div>

                            <span>
                              Reason
                            </span>

                            <strong>
                              {gap.gap_reason
                                || "Insufficient knowledge"}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Retrieved chunks
                            </span>

                            <strong>
                              {gap.retrieved_chunks
                                ?? 0}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Top score
                            </span>

                            <strong>
                              {gap.top_similarity
                                != null
                                ? Number(
                                  gap.top_similarity
                                ).toFixed(
                                  3
                                )
                                : "None"}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Recorded
                            </span>

                            <strong>
                              {formatDate(
                                gap.created_at
                              )}
                            </strong>

                          </div>

                        </div>

                      </article>
                    )
                  )}

                </div>
              )}

          </section>
        )}


        {/* =================================================
            CONFLICTS
            ================================================= */}

        {activeTab === "conflicts" && (
          <section className="rag-panel">

            <div className="rag-panel-header">

              <div>

                <span className="eyebrow">
                  POLICY SAFETY
                </span>

                <h2>
                  Detected Conflicts
                </h2>

                <p>
                  Contradictory active evidence detected
                  during Harbor retrieval.
                </p>

              </div>


              <span className="rag-count-pill rag-count-danger">
                {conflicts.length}
              </span>

            </div>


            {conflicts.length === 0
              ? (
                <div className="rag-empty-state">

                  <div>
                    ✓
                  </div>

                  <h3>
                    No policy conflicts
                  </h3>

                  <p>
                    No contradictory active evidence
                    has been detected.
                  </p>

                </div>
              )

              : (
                <div className="rag-record-list">

                  {conflicts.map(
                    (
                      conflict
                    ) => (
                      <article
                        key={
                          conflict.id
                        }
                        className="rag-record-card rag-conflict-card"
                      >

                        <div className="rag-record-top">

                          <div>

                            <span className="rag-record-label">
                              Question
                            </span>

                            <h3>
                              {conflict.question}
                            </h3>

                          </div>


                          <span className="rag-status-danger">
                            Conflict
                          </span>

                        </div>


                        <div className="rag-record-field">

                          <span>
                            Reason
                          </span>

                          <p>
                            {conflict.reason}
                          </p>

                        </div>


                        <div className="rag-chip-section">

                          <span>
                            Sources
                          </span>


                          <div className="rag-chip-list">

                            {(
                              conflict.source_names
                              || []
                            ).map(
                              (
                                source
                              ) => (
                                <span
                                  key={
                                    source
                                  }
                                  className="rag-source-chip"
                                >
                                  {source}
                                </span>
                              )
                            )}

                          </div>

                        </div>


                        <div className="rag-chip-section">

                          <span>
                            Logical keys
                          </span>


                          <div className="rag-chip-list">

                            {(
                              conflict.logical_keys
                              || []
                            ).map(
                              (
                                key
                              ) => (
                                <span
                                  key={
                                    key
                                  }
                                  className="rag-key-chip"
                                >
                                  {key}
                                </span>
                              )
                            )}

                          </div>

                        </div>


                        <div className="rag-record-meta">

                          <div>

                            <span>
                              Requester
                            </span>

                            <strong>
                              {formatLabel(
                                conflict.requester_role
                              )}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Detected
                            </span>

                            <strong>
                              {formatDate(
                                conflict.created_at
                              )}
                            </strong>

                          </div>

                        </div>

                      </article>
                    )
                  )}

                </div>
              )}

          </section>
        )}


        {/* =================================================
            FEEDBACK
            ================================================= */}

        {activeTab === "feedback" && (
          <section className="rag-panel">

            <div className="rag-panel-header rag-feedback-header">

              <div>

                <span className="eyebrow">
                  USER FEEDBACK
                </span>

                <h2>
                  RAG Feedback
                </h2>

                <p>
                  Review customer and staff ratings
                  of Harbor responses.
                </p>

              </div>


              <select
                className="rag-feedback-filter"
                value={
                  feedbackFilter
                }
                onChange={(event) =>
                  setFeedbackFilter(
                    event.target.value
                  )
                }
              >

                <option value="">
                  All feedback
                </option>

                <option value="positive">
                  Positive
                </option>

                <option value="negative">
                  Negative
                </option>

              </select>

            </div>


            {filteredFeedback.length === 0
              ? (
                <div className="rag-empty-state">

                  <div>
                    ◉
                  </div>

                  <h3>
                    No feedback yet
                  </h3>

                  <p>
                    User ratings will appear here.
                  </p>

                </div>
              )

              : (
                <div className="rag-record-list">

                  {filteredFeedback.map(
                    (
                      item
                    ) => (
                      <article
                        key={
                          item.id
                        }
                        className="rag-record-card"
                      >

                        <div className="rag-record-top">

                          <div>

                            <span className="rag-record-label">
                              Question
                            </span>

                            <h3>
                              {item.question}
                            </h3>

                          </div>


                          <span
                            className={
                              item.rating
                              === "positive"
                                ? "rag-status-positive"
                                : "rag-status-danger"
                            }
                          >
                            {item.rating
                            === "positive"
                              ? "👍 Positive"
                              : "👎 Negative"}
                          </span>

                        </div>


                        <div className="rag-record-field">

                          <span>
                            Harbor answer
                          </span>

                          <p>
                            {item.answer}
                          </p>

                        </div>


                        {item.comment && (
                          <div className="rag-feedback-comment">

                            <span>
                              Feedback comment
                            </span>

                            <p>
                              {item.comment}
                            </p>

                          </div>
                        )}


                        {item.source_names
                          ?.length > 0
                          && (
                            <div className="rag-chip-section">

                              <span>
                                Sources
                              </span>


                              <div className="rag-chip-list">

                                {item.source_names.map(
                                  (
                                    source
                                  ) => (
                                    <span
                                      key={
                                        source
                                      }
                                      className="rag-source-chip"
                                    >
                                      {source}
                                    </span>
                                  )
                                )}

                              </div>

                            </div>
                          )}


                        <div className="rag-record-meta">

                          <div>

                            <span>
                              Submitted
                            </span>

                            <strong>
                              {formatDate(
                                item.created_at
                              )}
                            </strong>

                          </div>

                        </div>

                      </article>
                    )
                  )}

                </div>
              )}

          </section>
        )}


        {/* =================================================
            EVALUATIONS
            ================================================= */}

        {activeTab === "evaluations" && (
          <>

            <section className="rag-evaluation-grid">

              {/* =========================================
                  CREATE CASE
                  ========================================= */}

              <article className="rag-panel">

                <div className="rag-panel-header">

                  <div>

                    <span className="eyebrow">
                      TEST SET
                    </span>

                    <h2>
                      Create evaluation case
                    </h2>

                    <p>
                      Add a reusable quality test
                      for Harbor RAG.
                    </p>

                  </div>

                </div>


                <form
                  className="rag-evaluation-form"
                  onSubmit={
                    handleCreateCase
                  }
                >

                  <label>

                    <span>
                      Question
                    </span>

                    <textarea
                      rows="3"
                      value={
                        evaluationQuestion
                      }
                      onChange={(event) =>
                        setEvaluationQuestion(
                          event.target.value
                        )
                      }
                      placeholder="What is the refund period?"
                      required
                    />

                  </label>


                  <label>

                    <span>
                      Expected answer phrases
                    </span>

                    <input
                      type="text"
                      value={
                        expectedAnswer
                      }
                      onChange={(event) =>
                        setExpectedAnswer(
                          event.target.value
                        )
                      }
                      placeholder="14 days"
                    />

                    <small>
                      Separate multiple phrases
                      with commas.
                    </small>

                  </label>


                  <label>

                    <span>
                      Expected sources
                    </span>

                    <input
                      type="text"
                      value={
                        expectedSources
                      }
                      onChange={(event) =>
                        setExpectedSources(
                          event.target.value
                        )
                      }
                      placeholder="refund_policy_v2.txt"
                    />

                    <small>
                      Separate multiple filenames
                      with commas.
                    </small>

                  </label>


                  <div className="rag-evaluation-form-row">

                    <label>

                      <span>
                        Requester role
                      </span>

                      <select
                        value={
                          requesterRole
                        }
                        onChange={(event) =>
                          setRequesterRole(
                            event.target.value
                          )
                        }
                      >

                        <option value="customer">
                          Customer
                        </option>

                        <option value="support_agent">
                          Support Agent
                        </option>

                        <option value="admin">
                          Admin
                        </option>

                      </select>

                    </label>


                    <label className="rag-grounded-checkbox">

                      <input
                        type="checkbox"
                        checked={
                          expectedGrounded
                        }
                        onChange={(event) =>
                          setExpectedGrounded(
                            event.target.checked
                          )
                        }
                      />

                      <span>
                        Expected grounded answer
                      </span>

                    </label>

                  </div>


                  <button
                    type="submit"
                    className="primary-button"
                    disabled={
                      creatingCase
                    }
                  >
                    {creatingCase
                      ? "Creating..."
                      : "Create test case"}
                  </button>

                </form>

              </article>


              {/* =========================================
                  RUN EVALUATION
                  ========================================= */}

              <article className="rag-panel">

                <div className="rag-panel-header">

                  <div>

                    <span className="eyebrow">
                      AUTOMATED TEST
                    </span>

                    <h2>
                      Run evaluation
                    </h2>

                    <p>
                      Execute all active RAG
                      quality test cases.
                    </p>

                  </div>

                </div>


                <div className="rag-run-summary">

                  <div className="rag-run-case-count">

                    <span>
                      Active cases
                    </span>

                    <strong>
                      {evaluationCases.length}
                    </strong>

                  </div>


                  <button
                    type="button"
                    className="rag-run-button"
                    disabled={
                      runningEvaluation
                      || evaluationCases.length
                      === 0
                    }
                    onClick={
                      handleRunEvaluation
                    }
                  >
                    {runningEvaluation
                      ? "Running evaluation..."
                      : "▶ Run full evaluation"}
                  </button>

                </div>


                {latestEvaluation && (
                  <div className="rag-latest-evaluation">

                    <span className="rag-record-label">
                      Latest result
                    </span>


                    <div className="rag-evaluation-metrics">

                      <div>

                        <span>
                          Overall
                        </span>

                        <strong>
                          {formatPercent(
                            latestEvaluation
                              .overall_pass_rate
                          )}
                        </strong>

                      </div>


                      <div>

                        <span>
                          Retrieval
                        </span>

                        <strong>
                          {formatPercent(
                            latestEvaluation
                              .retrieval_hit_rate
                          )}
                        </strong>

                      </div>


                      <div>

                        <span>
                          Groundedness
                        </span>

                        <strong>
                          {formatPercent(
                            latestEvaluation
                              .groundedness_accuracy
                          )}
                        </strong>

                      </div>


                      <div>

                        <span>
                          Sources
                        </span>

                        <strong>
                          {formatPercent(
                            latestEvaluation
                              .source_accuracy
                          )}
                        </strong>

                      </div>


                      <div>

                        <span>
                          Answers
                        </span>

                        <strong>
                          {formatPercent(
                            latestEvaluation
                              .answer_accuracy
                          )}
                        </strong>

                      </div>

                    </div>

                  </div>
                )}

              </article>

            </section>


            {/* =============================================
                EVALUATION CASES
                ============================================= */}

            <section className="rag-panel">

              <div className="rag-panel-header">

                <div>

                  <span className="eyebrow">
                    ACTIVE TEST SET
                  </span>

                  <h2>
                    Evaluation Cases
                  </h2>

                </div>


                <span className="rag-count-pill">
                  {evaluationCases.length}
                </span>

              </div>


              {evaluationCases.length === 0
                ? (
                  <div className="rag-empty-state">

                    <div>
                      ◫
                    </div>

                    <h3>
                      No evaluation cases
                    </h3>

                  </div>
                )

                : (
                  <div className="rag-case-table">

                    {evaluationCases.map(
                      (
                        testCase
                      ) => (
                        <article
                          key={
                            testCase.id
                          }
                          className="rag-test-case"
                        >

                          <div>

                            <span className="rag-record-label">
                              Question
                            </span>

                            <strong>
                              {testCase.question}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Expected grounded
                            </span>

                            <strong>
                              {testCase.expected_grounded
                                ? "Yes"
                                : "No"}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Role
                            </span>

                            <strong>
                              {formatLabel(
                                testCase.requester_role
                              )}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Sources
                            </span>

                            <strong>
                              {
                                (
                                  testCase.expected_sources
                                  || []
                                ).join(
                                  ", "
                                )
                                || "Not required"
                              }
                            </strong>

                          </div>

                        </article>
                      )
                    )}

                  </div>
                )}

            </section>


            {/* =============================================
                HISTORY
                ============================================= */}

            <section className="rag-panel">

              <div className="rag-panel-header">

                <div>

                  <span className="eyebrow">
                    QUALITY HISTORY
                  </span>

                  <h2>
                    Evaluation Runs
                  </h2>

                </div>

              </div>


              {evaluationRuns.length === 0
                ? (
                  <div className="rag-empty-state">

                    <div>
                      ◷
                    </div>

                    <h3>
                      No evaluation runs yet
                    </h3>

                  </div>
                )

                : (
                  <div className="rag-run-history">

                    {evaluationRuns.map(
                      (
                        run
                      ) => (
                        <article
                          key={
                            run.id
                          }
                          className="rag-run-history-row"
                        >

                          <div>

                            <span>
                              Run
                            </span>

                            <strong>
                              {String(
                                run.id
                              ).slice(
                                0,
                                8
                              )}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Cases
                            </span>

                            <strong>
                              {run.passed_cases}
                              /
                              {run.total_cases}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Overall
                            </span>

                            <strong>
                              {formatPercent(
                                run.overall_pass_rate
                              )}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Retrieval
                            </span>

                            <strong>
                              {formatPercent(
                                run.retrieval_hit_rate
                              )}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Grounded
                            </span>

                            <strong>
                              {formatPercent(
                                run.groundedness_accuracy
                              )}
                            </strong>

                          </div>


                          <div>

                            <span>
                              Date
                            </span>

                            <strong>
                              {formatDate(
                                run.created_at
                              )}
                            </strong>

                          </div>

                        </article>
                      )
                    )}

                  </div>
                )}

            </section>

          </>
        )}

      </main>

    </div>
  );
}
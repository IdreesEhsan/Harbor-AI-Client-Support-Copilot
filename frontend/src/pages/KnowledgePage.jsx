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
  activateKnowledgeDocument,
  deactivateKnowledgeDocument,
  deleteKnowledgeDocument,
  getKnowledgeDocuments,
  uploadKnowledgeDocument,
} from "../api/knowledge";

import {
  useAuth,
} from "../context/AuthContext";

import "../styles/knowledge.css";


export default function KnowledgePage() {
  const {
    user,
    logout,
  } = useAuth();


  /* =======================================================
     DOCUMENT STATE
     ======================================================= */

  const [
    documents,
    setDocuments,
  ] = useState([]);


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
    processingDocumentId,
    setProcessingDocumentId,
  ] = useState(null);


  /* =======================================================
     FILTER STATE
     ======================================================= */

  const [
    activeOnly,
    setActiveOnly,
  ] = useState(false);


  const [
    logicalKeyFilter,
    setLogicalKeyFilter,
  ] = useState("");


  const [
    visibilityFilter,
    setVisibilityFilter,
  ] = useState("");


  /* =======================================================
     UPLOAD FORM
     ======================================================= */

  const [
    file,
    setFile,
  ] = useState(null);


  const [
    logicalKey,
    setLogicalKey,
  ] = useState("");


  const [
    title,
    setTitle,
  ] = useState("");


  const [
    category,
    setCategory,
  ] = useState(
    "general"
  );


  const [
    version,
    setVersion,
  ] = useState(
    "1.0"
  );


  const [
    visibility,
    setVisibility,
  ] = useState(
    "public"
  );


  const [
    effectiveDate,
    setEffectiveDate,
  ] = useState("");


  const [
    uploading,
    setUploading,
  ] = useState(false);


  /* =======================================================
     HELPERS
     ======================================================= */

  const formatDate =
    (
      value
    ) => {
      if (!value) {
        return "Not set";
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
        return value;
      }


      return (
        date.toLocaleDateString(
          undefined,
          {
            year:
              "numeric",

            month:
              "short",

            day:
              "numeric",
          }
        )
      );
    };


  const formatDateTime =
    (
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
     LOAD DOCUMENTS
     ======================================================= */

  const loadDocuments =
    useCallback(
      async (
        showRefresh = false
      ) => {
        setError("");


        if (showRefresh) {
          setRefreshing(
            true
          );

        } else {
          setLoading(
            true
          );
        }


        try {
          const data =
            await getKnowledgeDocuments({
              activeOnly,

              logicalKey:
                logicalKeyFilter,

              visibility:
                visibilityFilter,
            });


          setDocuments(
            Array.isArray(
              data
            )
              ? data
              : []
          );

        } catch (err) {
          console.error(
            (
              "Unable to load "
              + "knowledge documents:"
            ),
            err
          );


          setError(
            err.response
              ?.data
              ?.detail
            || (
              "Unable to load "
              + "knowledge documents."
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
      [
        activeOnly,
        logicalKeyFilter,
        visibilityFilter,
      ]
    );


  useEffect(() => {
    loadDocuments();
  }, [
    loadDocuments,
  ]);


  /* =======================================================
     GROUP DOCUMENT VERSIONS
     ======================================================= */

  const groupedDocuments =
    useMemo(
      () => {
        const groups = {};


        for (
          const document
          of documents
        ) {
          const key =
            document.logical_key
            || document.source_name
            || document.id;


          if (!groups[key]) {
            groups[key] = [];
          }


          groups[key].push(
            document
          );
        }


        return (
          Object.entries(
            groups
          ).map(
            ([
              key,
              versions,
            ]) => ({
              logicalKey:
                key,

              versions:
                versions.sort(
                  (
                    first,
                    second
                  ) =>
                    new Date(
                      second.created_at
                      || 0
                    )
                    - new Date(
                      first.created_at
                      || 0
                    )
                ),
            })
          )
        );
      },
      [
        documents,
      ]
    );


  /* =======================================================
     RESET UPLOAD FORM
     ======================================================= */

  const resetUploadForm =
    () => {
      setFile(
        null
      );

      setLogicalKey(
        ""
      );

      setTitle(
        ""
      );

      setCategory(
        "general"
      );

      setVersion(
        "1.0"
      );

      setVisibility(
        "public"
      );

      setEffectiveDate(
        ""
      );


      const input =
        document.getElementById(
          "knowledge-file-input"
        );


      if (input) {
        input.value =
          "";
      }
    };


  /* =======================================================
     UPLOAD
     ======================================================= */

  const handleUpload =
    async (
      event
    ) => {
      event.preventDefault();


      if (!file) {
        setError(
          (
            "Choose a TXT, PDF, "
            + "or DOCX file."
          )
        );

        return;
      }


      if (
        !logicalKey.trim()
        || !title.trim()
        || !version.trim()
      ) {
        setError(
          (
            "Logical key, title, "
            + "and version are required."
          )
        );

        return;
      }


      setUploading(
        true
      );

      setError("");

      setSuccessMessage("");


      try {
        const result =
          await uploadKnowledgeDocument({
            file,

            logicalKey:
              logicalKey
                .trim()
                .toLowerCase(),

            title:
              title.trim(),

            category:
              category
                .trim()
                .toLowerCase(),

            version:
              version.trim(),

            visibility,

            effectiveDate,
          });


        if (
          result.status
          === "skipped"
        ) {
          setSuccessMessage(
            (
              "Identical document content "
              + "already exists. Harbor "
              + "reused the existing version."
            )
          );

        } else {
          setSuccessMessage(
            (
              "Knowledge document indexed "
              + "successfully."
            )
          );
        }


        resetUploadForm();


        await loadDocuments(
          true
        );

      } catch (err) {
        console.error(
          (
            "Knowledge upload "
            + "failed:"
          ),
          err
        );


        setError(
          err.response
            ?.data
            ?.detail
          || (
            "Unable to upload "
            + "knowledge document."
          )
        );

      } finally {
        setUploading(
          false
        );
      }
    };


  /* =======================================================
     ACTIVATE
     ======================================================= */

  const handleActivate =
    async (
      document
    ) => {
      const confirmed =
        window.confirm(
          (
            `Activate version ${
              document.version
              || "unknown"
            } of "${
              document.title
              || document.source_name
            }"?\n\n`
            + (
              "Any currently-active version "
              + "with the same logical key "
              + "will be deactivated."
            )
          )
        );


      if (!confirmed) {
        return;
      }


      setProcessingDocumentId(
        document.id
      );

      setError("");

      setSuccessMessage("");


      try {
        await activateKnowledgeDocument(
          document.id
        );


        setSuccessMessage(
          (
            `Version ${
              document.version
              || ""
            } activated successfully.`
          )
        );


        await loadDocuments(
          true
        );

      } catch (err) {
        console.error(
          (
            "Unable to activate "
            + "document version:"
          ),
          err
        );


        setError(
          err.response
            ?.data
            ?.detail
          || (
            "Unable to activate "
            + "this document version."
          )
        );

      } finally {
        setProcessingDocumentId(
          null
        );
      }
    };


  /* =======================================================
     DEACTIVATE
     ======================================================= */

  const handleDeactivate =
    async (
      document
    ) => {
      const confirmed =
        window.confirm(
          (
            `Deactivate version ${
              document.version
              || "unknown"
            } of "${
              document.title
              || document.source_name
            }"?\n\n`
            + (
              "Harbor will stop using this "
              + "version for RAG answers. "
              + "The document and its indexed "
              + "chunks will remain available "
              + "for future reactivation."
            )
          )
        );


      if (!confirmed) {
        return;
      }


      setProcessingDocumentId(
        document.id
      );

      setError("");

      setSuccessMessage("");


      try {
        await deactivateKnowledgeDocument(
          document.id
        );


        setSuccessMessage(
          (
            `Version ${
              document.version
              || ""
            } deactivated successfully.`
          )
        );


        await loadDocuments(
          true
        );

      } catch (err) {
        console.error(
          (
            "Unable to deactivate "
            + "document:"
          ),
          err
        );


        setError(
          err.response
            ?.data
            ?.detail
          || (
            "Unable to deactivate "
            + "this document version."
          )
        );

      } finally {
        setProcessingDocumentId(
          null
        );
      }
    };


  /* =======================================================
     DELETE
     ======================================================= */

  const handleDelete =
    async (
      document
    ) => {
      const name =
        document.title
        || document.source_name
        || "knowledge document";


      const activeWarning =
        document.is_active
          ? (
            "\n\nWARNING: This version is "
            + "currently active. Deleting it "
            + "will leave this policy without "
            + "an active version unless you "
            + "manually activate another one."
          )
          : "";


      const confirmed =
        window.confirm(
          (
            `Permanently delete "${name}" `
            + `version ${
              document.version
              || "unknown"
            }?`
            + activeWarning
            + (
              "\n\nThis will permanently "
              + "remove the document and all "
              + "indexed chunks. This action "
              + "cannot be undone."
            )
          )
        );


      if (!confirmed) {
        return;
      }


      /*
       * Extra confirmation for active policies because deleting
       * an active policy can immediately create a knowledge gap.
       */
      if (
        document.is_active
      ) {
        const secondConfirmation =
          window.confirm(
            (
              "This document is ACTIVE.\n\n"
              + "Are you sure you want to "
              + "permanently delete it?"
            )
          );


        if (!secondConfirmation) {
          return;
        }
      }


      setProcessingDocumentId(
        document.id
      );

      setError("");

      setSuccessMessage("");


      try {
        const result =
          await deleteKnowledgeDocument(
            document.id
          );


        setSuccessMessage(
          (
            `Version ${
              result.version
              || document.version
              || ""
            } deleted permanently.`
          )
        );


        await loadDocuments(
          true
        );

      } catch (err) {
        console.error(
          (
            "Unable to delete "
            + "knowledge document:"
          ),
          err
        );


        setError(
          err.response
            ?.data
            ?.detail
          || (
            "Unable to delete "
            + "this knowledge document."
          )
        );

      } finally {
        setProcessingDocumentId(
          null
        );
      }
    };


  /* =======================================================
     CLEAR FILTERS
     ======================================================= */

  const clearFilters =
    () => {
      setActiveOnly(
        false
      );

      setLogicalKeyFilter(
        ""
      );

      setVisibilityFilter(
        ""
      );
    };


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
          Loading Harbor knowledge...
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
                Knowledge
              </span>

            </div>

          </div>


          <div className="knowledge-top-navigation">

            <Link
              to="/staff"
              className="knowledge-nav-link"
            >
              Support Operations
            </Link>


            <Link
              to="/staff/knowledge"
              className={
                (
                  "knowledge-nav-link "
                  + "knowledge-nav-link-active"
                )
              }
            >
              Knowledge Base
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

      <main className="knowledge-page">

        {/* =================================================
            HERO
            ================================================= */}

        <section className="knowledge-hero">

          <div>

            <span className="eyebrow">
              KNOWLEDGE MANAGEMENT
            </span>


            <h1>
              Harbor Knowledge Base
            </h1>


            <p>
              Manage support policies, document versions,
              visibility, lifecycle status, and active
              knowledge used by Harbor AI.
            </p>

          </div>


          <button
            type="button"
            className="secondary-button"
            disabled={
              refreshing
            }
            onClick={() =>
              loadDocuments(
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
            MESSAGES
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
            STATISTICS
            ================================================= */}

        <section className="knowledge-stats-grid">

          <div className="stat-card glass-card">

            <div>

              <span>
                Documents
              </span>


              <strong>
                {documents.length}
              </strong>

            </div>

          </div>


          <div className="stat-card glass-card">

            <div>

              <span>
                Active
              </span>


              <strong>
                {
                  documents.filter(
                    (
                      document
                    ) =>
                      document.is_active
                  ).length
                }
              </strong>

            </div>

          </div>


          <div className="stat-card glass-card">

            <div>

              <span>
                Public
              </span>


              <strong>
                {
                  documents.filter(
                    (
                      document
                    ) =>
                      document.visibility
                      === "public"
                  ).length
                }
              </strong>

            </div>

          </div>


          <div className="stat-card glass-card">

            <div>

              <span>
                Staff only
              </span>


              <strong>
                {
                  documents.filter(
                    (
                      document
                    ) =>
                      document.visibility
                      === "staff_only"
                  ).length
                }
              </strong>

            </div>

          </div>

        </section>


        {/* =================================================
            UPLOAD
            ================================================= */}

        <section className="knowledge-upload-card glass-card">

          <div className="knowledge-section-header">

            <div>

              <span className="eyebrow">
                ADD KNOWLEDGE
              </span>


              <h2>
                Upload document version
              </h2>


              <p>
                Upload a new policy or a new version
                of an existing policy.
              </p>

            </div>

          </div>


          <form
            className="knowledge-upload-form"
            onSubmit={
              handleUpload
            }
          >

            <label className="knowledge-file-field">

              <span className="knowledge-field-label">
                Document
              </span>


              <input
                id="knowledge-file-input"
                type="file"
                accept=".txt,.pdf,.docx"
                onChange={(event) =>
                  setFile(
                    event.target.files
                      ?.[0]
                    || null
                  )
                }
              />


              <small>
                TXT, PDF or DOCX
              </small>

            </label>


            <div className="knowledge-form-grid">

              <label>

                <span>
                  Logical key
                </span>


                <input
                  type="text"
                  value={
                    logicalKey
                  }
                  onChange={(event) =>
                    setLogicalKey(
                      event.target.value
                    )
                  }
                  placeholder="refund-policy"
                  required
                />

              </label>


              <label>

                <span>
                  Title
                </span>


                <input
                  type="text"
                  value={
                    title
                  }
                  onChange={(event) =>
                    setTitle(
                      event.target.value
                    )
                  }
                  placeholder="Refund Policy"
                  required
                />

              </label>


              <label>

                <span>
                  Category
                </span>


                <input
                  type="text"
                  value={
                    category
                  }
                  onChange={(event) =>
                    setCategory(
                      event.target.value
                    )
                  }
                  placeholder="refund"
                />

              </label>


              <label>

                <span>
                  Version
                </span>


                <input
                  type="text"
                  value={
                    version
                  }
                  onChange={(event) =>
                    setVersion(
                      event.target.value
                    )
                  }
                  placeholder="2.0"
                  required
                />

              </label>


              <label>

                <span>
                  Visibility
                </span>


                <select
                  value={
                    visibility
                  }
                  onChange={(event) =>
                    setVisibility(
                      event.target.value
                    )
                  }
                >

                  <option value="public">
                    Public
                  </option>


                  <option value="staff_only">
                    Staff only
                  </option>

                </select>

              </label>


              <label>

                <span>
                  Effective date
                </span>


                <input
                  type="date"
                  value={
                    effectiveDate
                  }
                  onChange={(event) =>
                    setEffectiveDate(
                      event.target.value
                    )
                  }
                />

              </label>

            </div>


            <div className="knowledge-upload-actions">

              <button
                type="button"
                className="ghost-button"
                disabled={
                  uploading
                }
                onClick={
                  resetUploadForm
                }
              >
                Clear
              </button>


              <button
                type="submit"
                className="primary-button"
                disabled={
                  uploading
                  || !file
                }
              >
                {uploading
                  ? "Indexing..."
                  : "Upload & Index"}
              </button>

            </div>

          </form>

        </section>


        {/* =================================================
            FILTERS
            ================================================= */}

        <section className="knowledge-filter-bar glass-card">

          <div className="knowledge-filter-search">

            <span>
              Logical key
            </span>


            <input
              type="text"
              value={
                logicalKeyFilter
              }
              onChange={(event) =>
                setLogicalKeyFilter(
                  event.target.value
                )
              }
              placeholder="Filter by logical key..."
            />

          </div>


          <label className="knowledge-filter-select">

            <span>
              Visibility
            </span>


            <select
              value={
                visibilityFilter
              }
              onChange={(event) =>
                setVisibilityFilter(
                  event.target.value
                )
              }
            >

              <option value="">
                All visibility
              </option>


              <option value="public">
                Public
              </option>


              <option value="staff_only">
                Staff only
              </option>

            </select>

          </label>


          <label className="knowledge-checkbox">

            <input
              type="checkbox"
              checked={
                activeOnly
              }
              onChange={(event) =>
                setActiveOnly(
                  event.target.checked
                )
              }
            />


            <span>
              Active only
            </span>

          </label>


          {(activeOnly
            || logicalKeyFilter
            || visibilityFilter) && (
            <button
              type="button"
              className="clear-filter-button"
              onClick={
                clearFilters
              }
            >
              Clear filters
            </button>
          )}

        </section>


        {/* =================================================
            DOCUMENT LIST
            ================================================= */}

        <section className="knowledge-list-panel glass-card">

          <div className="knowledge-section-header">

            <div>

              <span className="eyebrow">
                INDEXED KNOWLEDGE
              </span>


              <h2>
                Documents & versions
              </h2>

            </div>


            <span className="knowledge-result-count">
              {documents.length}
              {" "}
              {documents.length === 1
                ? "document"
                : "documents"}
            </span>

          </div>


          {groupedDocuments.length === 0
            ? (
              <div className="knowledge-empty">

                <div>
                  ◫
                </div>


                <h3>
                  No knowledge documents found
                </h3>


                <p>
                  Upload a document or change
                  the current filters.
                </p>

              </div>
            )

            : (
              <div className="knowledge-groups">

                {groupedDocuments.map(
                  (
                    group
                  ) => (
                    <article
                      key={
                        group.logicalKey
                      }
                      className="knowledge-group"
                    >

                      <div className="knowledge-group-header">

                        <div>

                          <span className="knowledge-logical-key">
                            {
                              group.logicalKey
                            }
                          </span>


                          <h3>
                            {
                              group.versions[0]
                                ?.title
                              || group.logicalKey
                            }
                          </h3>

                        </div>


                        <span className="knowledge-version-count">

                          {
                            group.versions.length
                          }
                          {" "}
                          {
                            group.versions.length
                            === 1
                              ? "version"
                              : "versions"
                          }

                        </span>

                      </div>


                      <div className="knowledge-version-list">

                        {group.versions.map(
                          (
                            document
                          ) => {
                            const processing =
                              processingDocumentId
                              === document.id;


                            return (
                              <div
                                key={
                                  document.id
                                }
                                className={
                                  document.is_active
                                    ? (
                                      "knowledge-version-card "
                                      + "knowledge-version-active"
                                    )
                                    : "knowledge-version-card"
                                }
                              >

                                <div className="knowledge-version-main">

                                  <div className="knowledge-version-title-row">

                                    <strong>
                                      Version{" "}
                                      {
                                        document.version
                                        || "Unknown"
                                      }
                                    </strong>


                                    <div className="knowledge-version-badges">

                                      <span
                                        className={
                                          document.is_active
                                            ? "badge badge-success"
                                            : "badge"
                                        }
                                      >
                                        {document.is_active
                                          ? "Active"
                                          : "Inactive"}
                                      </span>


                                      <span
                                        className={
                                          document.visibility
                                          === "staff_only"
                                            ? "badge badge-warning"
                                            : "badge badge-success"
                                        }
                                      >
                                        {document.visibility
                                        === "staff_only"
                                          ? "Staff only"
                                          : "Public"}
                                      </span>

                                    </div>

                                  </div>


                                  <div className="knowledge-version-meta">

                                    <div>

                                      <span>
                                        Source
                                      </span>


                                      <strong>
                                        {
                                          document.source_name
                                        }
                                      </strong>

                                    </div>


                                    <div>

                                      <span>
                                        Category
                                      </span>


                                      <strong>
                                        {formatLabel(
                                          document.category
                                        )}
                                      </strong>

                                    </div>


                                    <div>

                                      <span>
                                        Effective
                                      </span>


                                      <strong>
                                        {formatDate(
                                          document.effective_date
                                        )}
                                      </strong>

                                    </div>


                                    <div>

                                      <span>
                                        Indexed
                                      </span>


                                      <strong>
                                        {formatDateTime(
                                          document.last_indexed_at
                                          || document.created_at
                                        )}
                                      </strong>

                                    </div>

                                  </div>

                                </div>


                                {/* =========================
                                    VERSION ACTIONS
                                    ========================= */}

                                <div className="knowledge-version-actions">

                                  {document.is_active
                                    ? (
                                      <button
                                        type="button"
                                        className="secondary-button"
                                        disabled={
                                          processing
                                        }
                                        onClick={() =>
                                          handleDeactivate(
                                            document
                                          )
                                        }
                                      >
                                        {processing
                                          ? "Processing..."
                                          : "Deactivate"}
                                      </button>
                                    )

                                    : (
                                      <button
                                        type="button"
                                        className="secondary-button"
                                        disabled={
                                          processing
                                        }
                                        onClick={() =>
                                          handleActivate(
                                            document
                                          )
                                        }
                                      >
                                        {processing
                                          ? "Processing..."
                                          : "Activate version"}
                                      </button>
                                    )}


                                  <button
                                    type="button"
                                    className="knowledge-delete-button"
                                    disabled={
                                      processing
                                    }
                                    onClick={() =>
                                      handleDelete(
                                        document
                                      )
                                    }
                                  >
                                    {processing
                                      ? "Processing..."
                                      : "Delete"}
                                  </button>

                                </div>

                              </div>
                            );
                          }
                        )}

                      </div>

                    </article>
                  )
                )}

              </div>
            )}

        </section>

      </main>

    </div>
  );
}
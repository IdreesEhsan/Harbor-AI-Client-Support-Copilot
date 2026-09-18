import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  submitRagFeedback,
} from "../api/rag";

import "../styles/rag-feedback.css";


export default function RagFeedback({
  messageId,
  question,
  answer,
  citations = [],
}) {
  const [
    selectedRating,
    setSelectedRating,
  ] = useState(null);


  const [
    comment,
    setComment,
  ] = useState("");


  const [
    showComment,
    setShowComment,
  ] = useState(false);


  const [
    submitting,
    setSubmitting,
  ] = useState(false);


  const [
    submitted,
    setSubmitted,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  /* =======================================================
     STORAGE KEY
     ======================================================= */

  const storageKey =
    useMemo(
      () => {
        if (!messageId) {
          return null;
        }


        return (
          `harbor-rag-feedback-${messageId}`
        );
      },
      [
        messageId,
      ]
    );


  /* =======================================================
     RESTORE SUBMITTED STATE
     ======================================================= */

  useEffect(() => {
    if (!storageKey) {
      return;
    }


    try {
      const saved =
        window.localStorage
          .getItem(
            storageKey
          );


      if (!saved) {
        return;
      }


      const parsed =
        JSON.parse(
          saved
        );


      if (
        parsed?.submitted
      ) {
        setSubmitted(
          true
        );

        setSelectedRating(
          parsed.rating
          || null
        );
      }

    } catch (storageError) {
      console.warn(
        "Unable to restore Harbor feedback state:",
        storageError
      );
    }
  }, [
    storageKey,
  ]);


  /* =======================================================
     SOURCE NAMES
     ======================================================= */

  const sourceNames =
    useMemo(
      () =>
        Array.from(
          new Set(
            (
              citations
              || []
            )
              .map(
                (
                  citation
                ) =>
                  citation?.source
              )
              .filter(
                Boolean
              )
          )
        ),
      [
        citations,
      ]
    );


  /* =======================================================
     SAVE SUBMISSION STATE
     ======================================================= */

  const saveSubmittedState =
    (
      rating
    ) => {
      if (!storageKey) {
        return;
      }


      try {
        window.localStorage
          .setItem(
            storageKey,
            JSON.stringify({
              submitted:
                true,

              rating,
            })
          );

      } catch (storageError) {
        console.warn(
          "Unable to save Harbor feedback state:",
          storageError
        );
      }
    };


  /* =======================================================
     SUBMIT FEEDBACK
     ======================================================= */

  const submitFeedback =
    async (
      rating,
      feedbackComment = null
    ) => {
      if (
        submitted
        || submitting
      ) {
        return;
      }


      if (
        !question?.trim()
        || !answer?.trim()
      ) {
        setError(
          "Unable to submit feedback for this answer."
        );

        return;
      }


      setSubmitting(
        true
      );

      setError("");


      try {
        await submitRagFeedback({
          question:
            question.trim(),

          answer:
            answer.trim(),

          rating,

          comment:
            feedbackComment
              ?.trim()
            || null,

          sourceNames,
        });


        setSelectedRating(
          rating
        );

        setSubmitted(
          true
        );

        setShowComment(
          false
        );


        saveSubmittedState(
          rating
        );

      } catch (requestError) {
        console.error(
          "Unable to submit Harbor feedback:",
          requestError
        );


        setError(
          requestError.response
            ?.data
            ?.detail
          || (
            "Unable to submit feedback. "
            + "Please try again."
          )
        );

      } finally {
        setSubmitting(
          false
        );
      }
    };


  /* =======================================================
     POSITIVE
     ======================================================= */

  const handlePositive =
    async () => {
      setSelectedRating(
        "positive"
      );

      setShowComment(
        false
      );

      setComment("");


      await submitFeedback(
        "positive"
      );
    };


  /* =======================================================
     NEGATIVE
     ======================================================= */

  const handleNegative =
    () => {
      if (
        submitted
        || submitting
      ) {
        return;
      }


      setSelectedRating(
        "negative"
      );

      setShowComment(
        true
      );

      setError("");
    };


  /* =======================================================
     NEGATIVE SUBMIT
     ======================================================= */

  const handleNegativeSubmit =
    async (
      event
    ) => {
      event.preventDefault();


      await submitFeedback(
        "negative",
        comment
      );
    };


  /* =======================================================
     CANCEL
     ======================================================= */

  const handleCancel =
    () => {
      if (submitting) {
        return;
      }


      setSelectedRating(
        null
      );

      setShowComment(
        false
      );

      setComment("");

      setError("");
    };


  /* =======================================================
     SUCCESS
     ======================================================= */

  if (submitted) {
    return (
      <div className="rag-feedback-success">

        <span className="rag-feedback-success-icon">
          ✓
        </span>


        <span className="rag-feedback-success-copy">
          Thanks for your feedback.
        </span>


        <span
          className={
            selectedRating
            === "positive"
              ? (
                "rag-feedback-success-rating "
                + "rag-feedback-success-rating-positive"
              )
              : (
                "rag-feedback-success-rating "
                + "rag-feedback-success-rating-negative"
              )
          }
        >
          {selectedRating
          === "positive"
            ? "👍 Helpful"
            : "👎 Not helpful"}
        </span>

      </div>
    );
  }


  /* =======================================================
     UI
     ======================================================= */

  return (
    <div className="rag-feedback">

      <div className="rag-feedback-main">

        <span className="rag-feedback-question">
          Was this helpful?
        </span>


        <div className="rag-feedback-actions">

          <button
            type="button"
            className={
              selectedRating
              === "positive"
                ? (
                  "rag-feedback-button "
                  + "rag-feedback-button-active-positive"
                )
                : "rag-feedback-button"
            }
            disabled={
              submitting
            }
            onClick={
              handlePositive
            }
          >

            <span className="rag-feedback-button-icon">
              👍
            </span>

            Helpful

          </button>


          <button
            type="button"
            className={
              selectedRating
              === "negative"
                ? (
                  "rag-feedback-button "
                  + "rag-feedback-button-active-negative"
                )
                : "rag-feedback-button"
            }
            disabled={
              submitting
            }
            onClick={
              handleNegative
            }
          >

            <span className="rag-feedback-button-icon">
              👎
            </span>

            Not helpful

          </button>

        </div>

      </div>


      {showComment && (
        <form
          className="rag-feedback-comment-form"
          onSubmit={
            handleNegativeSubmit
          }
        >

          <label>

            <span>
              What could Harbor improve?
            </span>


            <textarea
              rows="3"
              maxLength="2000"
              value={
                comment
              }
              onChange={(event) =>
                setComment(
                  event.target.value
                )
              }
              placeholder="Optional feedback about this answer..."
              disabled={
                submitting
              }
            />

          </label>


          <div className="rag-feedback-comment-footer">

            <span>
              Comment is optional.
            </span>


            <div>

              <button
                type="button"
                className="rag-feedback-cancel"
                disabled={
                  submitting
                }
                onClick={
                  handleCancel
                }
              >
                Cancel
              </button>


              <button
                type="submit"
                className="rag-feedback-submit"
                disabled={
                  submitting
                }
              >
                {submitting
                  ? "Submitting..."
                  : "Submit feedback"}
              </button>

            </div>

          </div>

        </form>
      )}


      {error && (
        <div className="rag-feedback-error">
          {error}
        </div>
      )}

    </div>
  );
}
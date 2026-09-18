import apiClient from "./client";


/* =========================================================
   SUBMIT RAG FEEDBACK
   ========================================================= */

export async function submitRagFeedback({
  question,
  answer,
  rating,
  comment = null,
  sourceNames = [],
}) {
  const response =
    await apiClient.post(
      "/rag/feedback",
      {
        question,
        answer,
        rating,
        comment,
        source_names:
          sourceNames,
      }
    );


  return response.data;
}
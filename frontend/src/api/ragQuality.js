import apiClient from "./client";


/* =========================================================
   ANALYTICS
   ========================================================= */

export async function getRagAnalytics() {
  const response =
    await apiClient.get(
      "/knowledge/analytics"
    );

  return response.data;
}


/* =========================================================
   KNOWLEDGE GAPS
   ========================================================= */

export async function getKnowledgeGaps(
  limit = 100
) {
  const response =
    await apiClient.get(
      "/knowledge/knowledge-gaps",
      {
        params: {
          limit,
        },
      }
    );

  return response.data;
}


/* =========================================================
   POLICY CONFLICTS
   ========================================================= */

export async function getPolicyConflicts(
  limit = 100
) {
  const response =
    await apiClient.get(
      "/knowledge/conflicts",
      {
        params: {
          limit,
        },
      }
    );

  return response.data;
}


/* =========================================================
   FEEDBACK
   ========================================================= */

export async function getRagFeedback({
  rating = "",
  limit = 100,
} = {}) {
  const params = {
    limit,
  };


  if (rating) {
    params.rating =
      rating;
  }


  const response =
    await apiClient.get(
      "/knowledge/feedback",
      {
        params,
      }
    );

  return response.data;
}


/* =========================================================
   EVALUATION CASES
   ========================================================= */

export async function getEvaluationCases(
  activeOnly = true
) {
  const response =
    await apiClient.get(
      "/knowledge/evaluation/cases",
      {
        params: {
          active_only:
            activeOnly,
        },
      }
    );

  return response.data;
}


export async function createEvaluationCase({
  question,
  expectedAnswerContains,
  expectedSources,
  expectedGrounded,
  requesterRole,
}) {
  const response =
    await apiClient.post(
      "/knowledge/evaluation/cases",
      {
        question,

        expected_answer_contains:
          expectedAnswerContains,

        expected_sources:
          expectedSources,

        expected_grounded:
          expectedGrounded,

        requester_role:
          requesterRole,
      }
    );

  return response.data;
}


/* =========================================================
   EVALUATION RUN
   ========================================================= */

export async function runRagEvaluation() {
  const response =
    await apiClient.post(
      "/knowledge/evaluation/run"
    );

  return response.data;
}


/* =========================================================
   EVALUATION HISTORY
   ========================================================= */

export async function getEvaluationRuns(
  limit = 50
) {
  const response =
    await apiClient.get(
      "/knowledge/evaluation/runs",
      {
        params: {
          limit,
        },
      }
    );

  return response.data;
}
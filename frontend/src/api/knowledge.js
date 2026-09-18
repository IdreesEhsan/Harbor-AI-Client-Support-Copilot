import apiClient from "./client";


/* =========================================================
   KNOWLEDGE DOCUMENTS
   ========================================================= */

export async function getKnowledgeDocuments({
  activeOnly = false,
  logicalKey = "",
  visibility = "",
} = {}) {
  const params = {
    active_only:
      activeOnly,
  };


  if (
    logicalKey.trim()
  ) {
    params.logical_key =
      logicalKey.trim();
  }


  if (visibility) {
    params.visibility =
      visibility;
  }


  const response =
    await apiClient.get(
      "/knowledge/documents",
      {
        params,
      }
    );


  return response.data;
}


/* =========================================================
   UPLOAD DOCUMENT VERSION
   ========================================================= */

export async function uploadKnowledgeDocument({
  file,
  logicalKey,
  title,
  category,
  version,
  visibility,
  effectiveDate,
}) {
  const formData =
    new FormData();


  formData.append(
    "file",
    file
  );


  formData.append(
    "logical_key",
    logicalKey
  );


  formData.append(
    "title",
    title
  );


  formData.append(
    "category",
    category
      || "general"
  );


  formData.append(
    "version",
    version
  );


  formData.append(
    "visibility",
    visibility
      || "public"
  );


  if (effectiveDate) {
    formData.append(
      "effective_date",
      effectiveDate
    );
  }


  const response =
    await apiClient.post(
      "/knowledge/documents",
      formData
    );


  return response.data;
}


/* =========================================================
   ACTIVATE DOCUMENT
   ========================================================= */

export async function activateKnowledgeDocument(
  documentId
) {
  const response =
    await apiClient.post(
      `/knowledge/documents/${documentId}/activate`
    );


  return response.data;
}


/* =========================================================
   DEACTIVATE DOCUMENT
   ========================================================= */

export async function deactivateKnowledgeDocument(
  documentId
) {
  const response =
    await apiClient.post(
      `/knowledge/documents/${documentId}/deactivate`
    );


  return response.data;
}


/* =========================================================
   DELETE DOCUMENT
   ========================================================= */

export async function deleteKnowledgeDocument(
  documentId
) {
  const response =
    await apiClient.delete(
      `/knowledge/documents/${documentId}`
    );


  return response.data;
}
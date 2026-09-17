import apiClient from "./client";


/* =========================================================
   GET SIDEBAR CONVERSATIONS
   ========================================================= */

export async function getConversations() {
  const response =
    await apiClient.get(
      "/conversations"
    );

  return response.data;
}


/* =========================================================
   GET ONE COMPLETE CONVERSATION
   ========================================================= */

export async function getConversation(
  conversationId
) {
  const response =
    await apiClient.get(
      `/conversations/${conversationId}`
    );

  return response.data;
}
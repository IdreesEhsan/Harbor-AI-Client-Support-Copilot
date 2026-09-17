import apiClient from "./client";


/* =========================================================
   CUSTOMER TICKETS
   ========================================================= */

export async function getMyCases() {
  const response =
    await apiClient.get(
      "/tickets/mine"
    );

  return response.data;
}


export async function getMyCase(
  ticketId
) {
  const response =
    await apiClient.get(
      `/tickets/mine/${ticketId}`
    );

  return response.data;
}


/* =========================================================
   CUSTOMER CONVERSATION
   ========================================================= */

export async function getMyCaseUpdates(
  ticketId
) {
  const response =
    await apiClient.get(
      `/tickets/mine/${ticketId}/updates`
    );

  return response.data;
}


export async function replyToMyCase(
  ticketId,
  content
) {
  const response =
    await apiClient.post(
      `/tickets/mine/${ticketId}/updates`,
      {
        content,
      }
    );

  return response.data;
}


/* =========================================================
   STAFF TICKETS
   ========================================================= */

export async function getTickets() {
  const response =
    await apiClient.get(
      "/tickets"
    );

  return response.data;
}


export async function getTicket(
  ticketId
) {
  const response =
    await apiClient.get(
      `/tickets/${ticketId}`
    );

  return response.data;
}


/* =========================================================
   STAFF CONVERSATION
   ========================================================= */

export async function getTicketUpdates(
  ticketId
) {
  const response =
    await apiClient.get(
      `/tickets/${ticketId}/updates`
    );

  return response.data;
}


export async function replyToTicket(
  ticketId,
  content
) {
  const response =
    await apiClient.post(
      `/tickets/${ticketId}/updates`,
      {
        update_type:
          "staff_reply",

        content,
      }
    );

  return response.data;
}


export async function addInternalNote(
  ticketId,
  content
) {
  const response =
    await apiClient.post(
      `/tickets/${ticketId}/updates`,
      {
        update_type:
          "internal_note",

        content,
      }
    );

  return response.data;
}


/* =========================================================
   STAFF APPROVAL
   ========================================================= */

export async function reviewTicket(
  ticketId,
  approved
) {
  const response =
    await apiClient.post(
      `/tickets/${ticketId}/approval`,
      {
        approved,
      }
    );

  return response.data;
}


/* =========================================================
   STAFF EXECUTION
   ========================================================= */

export async function executeTicket(
  ticketId
) {
  const response =
    await apiClient.post(
      `/tickets/${ticketId}/execute`
    );

  return response.data;
}
import apiClient from "./client";


/* =========================================================
   CUSTOMER TICKETS
   ========================================================= */

/**
 * Return support tickets belonging to the authenticated
 * customer.
 */
export async function getMyCases() {
  const response =
    await apiClient.get(
      "/tickets/mine"
    );

  return response.data;
}


/**
 * Return one support ticket belonging to the authenticated
 * customer.
 */
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
   CUSTOMER TICKET CONVERSATION
   ========================================================= */

/**
 * Return customer-visible conversation entries.
 *
 * The backend excludes internal staff notes.
 */
export async function getMyCaseUpdates(
  ticketId
) {
  const response =
    await apiClient.get(
      `/tickets/mine/${ticketId}/updates`
    );

  return response.data;
}


/**
 * Add a customer reply to a support case.
 */
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

/**
 * Return all Harbor support tickets available to
 * authenticated support staff.
 */
export async function getTickets() {
  const response =
    await apiClient.get(
      "/tickets"
    );

  return response.data;
}


/**
 * Return one support ticket for staff review.
 */
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
   STAFF TICKET CONVERSATION
   ========================================================= */

/**
 * Return the complete ticket timeline for staff.
 *
 * This includes internal notes.
 */
export async function getTicketUpdates(
  ticketId
) {
  const response =
    await apiClient.get(
      `/tickets/${ticketId}/updates`
    );

  return response.data;
}


/**
 * Add a customer-visible support-agent reply.
 */
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


/**
 * Add an internal support note.
 *
 * Internal notes must never be exposed by the customer
 * endpoint.
 */
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

/**
 * Approve or reject a pending support ticket.
 */
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

/**
 * Execute a previously approved support ticket.
 *
 * Backend remains responsible for:
 *
 * - approval verification
 * - execution claims
 * - idempotency
 * - Monday synchronization
 * - persistence
 */
export async function executeTicket(
  ticketId
) {
  const response =
    await apiClient.post(
      `/tickets/${ticketId}/execute`
    );

  return response.data;
}
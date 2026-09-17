import apiClient from "./client";


/* =========================================================
   CUSTOMER TICKETS
   ========================================================= */

/**
 * Retrieve support tickets belonging only to the
 * authenticated customer.
 */
export async function getMyCases() {
  const response =
    await apiClient.get(
      "/tickets/mine"
    );

  return response.data;
}


/**
 * Retrieve one customer-owned support ticket.
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
   STAFF TICKETS
   ========================================================= */

/**
 * Retrieve all Harbor support tickets available to
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
 * Retrieve one support ticket for staff review.
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


/**
 * Execute a previously approved support ticket.
 *
 * The backend remains responsible for approval verification,
 * execution claims, idempotency, and external integrations.
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
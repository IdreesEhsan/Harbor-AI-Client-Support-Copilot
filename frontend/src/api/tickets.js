import apiClient from "./client";

/**
 * Retrieve support tickets available to the authenticated staff user.
 */
export async function getTickets() {
  const response = await apiClient.get("/tickets");
  return response.data;
}

/**
 * Retrieve one support ticket by its Harbor ticket ID.
 */
export async function getTicket(ticketId) {
  const response = await apiClient.get(`/tickets/${ticketId}`);
  return response.data;
}

/**
 * Approve or reject a pending support ticket.
 */
export async function reviewTicket(ticketId, approved) {
  const response = await apiClient.post(
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
 * execution claims, idempotency, and Monday.com integration.
 */
export async function executeTicket(ticketId) {
  const response = await apiClient.post(
    `/tickets/${ticketId}/execute`
  );

  return response.data;
}
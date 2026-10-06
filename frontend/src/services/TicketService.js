import { BASE_URL, getAuthHeaders, handleResponse } from '@/services/api.js';

export async function getTickets() {
    const response = await fetch(`${BASE_URL}/tickets/`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function createTicket(client_id, title, description) {
    const response = await fetch(`${BASE_URL}/tickets/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ client_id, title, description })
    });
    return handleResponse(response);
}

export async function updateTicket(id, title, description) {
    const response = await fetch(`${BASE_URL}/tickets/${id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ title, description })
    });
    return handleResponse(response);
}

export async function updateTicketStatus(id, status) {
    const response = await fetch(`${BASE_URL}/tickets/${id}/status`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ status })
    });
    return handleResponse(response);
}

export async function deleteTicket(id) {
    const response = await fetch(`${BASE_URL}/tickets/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

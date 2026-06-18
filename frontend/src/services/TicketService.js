import { BASE_URL, getAuthHeaders } from '@/services/api.js';

async function handleResponse(response) {
    if (response.status === 401) {
        const err = new Error('Session expired. Please log in again.');
        err.status = 401;
        throw err;
    }
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail ?? 'Request failed.');
    }
    if (response.status === 204) return null;
    return response.json();
}

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

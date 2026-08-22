import { BASE_URL, getAuthHeaders } from '@/services/api.js';

async function handleResponse(response) {
    if (response.status === 401) {
        const err = new Error('Session expired. Please log in again.');
        err.status = 401;
        throw err;
    }
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const err = new Error(data.detail ?? 'Request failed.');
        err.status = response.status;
        throw err;
    }
    if (response.status === 204) return null;
    return response.json();
}

export async function fetchContacts() {
    const response = await fetch(`${BASE_URL}/contacts/`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function triggerImport() {
    const response = await fetch(`${BASE_URL}/contacts/import`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function updateContactName(id, name) {
    const response = await fetch(`${BASE_URL}/contacts/${id}/name`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ name })
    });
    return handleResponse(response);
}

export async function updateContactOptedOut(id, optedOut) {
    const response = await fetch(`${BASE_URL}/contacts/${id}/opted_out`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ opted_out: optedOut })
    });
    return handleResponse(response);
}

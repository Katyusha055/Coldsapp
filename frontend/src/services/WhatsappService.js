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

export async function getStatus() {
    const response = await fetch(`${BASE_URL}/whatsapp/status`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function getQR() {
    const response = await fetch(`${BASE_URL}/whatsapp`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function getPendingContacts() {
    const response = await fetch(`${BASE_URL}/whatsapp/pending`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function updatePendingStatus(id, status) {
    const response = await fetch(`${BASE_URL}/whatsapp/pending/${id}/status`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ status })
    });
    return handleResponse(response);
}

export async function deletePending(id) {
    const response = await fetch(`${BASE_URL}/whatsapp/pending/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function setNotificationsEnabled(enabled) {
    const response = await fetch(`${BASE_URL}/whatsapp/notifications`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ enabled })
    });
    return handleResponse(response);
}

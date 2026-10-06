import { BASE_URL, getAuthHeaders, handleResponse } from '@/services/api.js';

export async function getStatus() {
    const response = await fetch(`${BASE_URL}/whatsapp/status`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function getQR() {
    const response = await fetch(`${BASE_URL}/whatsapp/`, {
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

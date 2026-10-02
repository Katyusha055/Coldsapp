import { BASE_URL, getAuthHeaders, handleResponse } from '@/services/api.js';

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

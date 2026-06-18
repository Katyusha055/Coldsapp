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

export async function getClients() {
    const response = await fetch(`${BASE_URL}/clients/`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function createClient(data) {
    const response = await fetch(`${BASE_URL}/clients/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ name: data.name, phone: data.phone, description: data.description })
    });
    return handleResponse(response);
}

export async function updateClient(id, data) {
    const response = await fetch(`${BASE_URL}/clients/${id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(data)
    });
    return handleResponse(response);
}

export async function deleteClient(id) {
    const response = await fetch(`${BASE_URL}/clients/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

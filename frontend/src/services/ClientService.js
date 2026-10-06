import { BASE_URL, getAuthHeaders, handleResponse } from '@/services/api.js';

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
        body: JSON.stringify(data)
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

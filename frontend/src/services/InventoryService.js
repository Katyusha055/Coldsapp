import { BASE_URL, getAuthHeaders, handleResponse } from '@/services/api.js';

export async function getItems() {
    const response = await fetch(`${BASE_URL}/items/`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function createItem(name, quantity) {
    const response = await fetch(`${BASE_URL}/items/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ name, quantity })
    });
    return handleResponse(response);
}

// data holds only the fields being changed: an omitted field is left alone,
// while an explicit null low_stock_threshold turns the alert off.
export async function updateItem(id, data) {
    const response = await fetch(`${BASE_URL}/items/${id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(data)
    });
    return handleResponse(response);
}

export async function deactivateItem(id) {
    const response = await fetch(`${BASE_URL}/items/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function addMovement(id, type, quantity, note = null) {
    const response = await fetch(`${BASE_URL}/items/${id}/movements`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ type, quantity, note })
    });
    return handleResponse(response);
}

export async function getMovements(id) {
    const response = await fetch(`${BASE_URL}/items/${id}/movements`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function countItem(id, counted) {
    const response = await fetch(`${BASE_URL}/items/${id}/count`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ counted })
    });
    return handleResponse(response);
}

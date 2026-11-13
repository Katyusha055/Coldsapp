import { BASE_URL, getAuthHeaders, handleResponse } from '@/services/api.js';

export async function getItems() {
    const response = await fetch(`${BASE_URL}/items/`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

// One item's current state, used to resync the cached copy after a 404 shows
// it changed on another device.
export async function getItem(id) {
    const response = await fetch(`${BASE_URL}/items/${id}`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

// code is optional: when given, the item is created already linked to it.
export async function createItem(name, quantity, lowStockThreshold = null, code = null) {
    const body = { name, quantity, low_stock_threshold: lowStockThreshold };
    if (code !== null) body.code = code;
    const response = await fetch(`${BASE_URL}/items/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body)
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

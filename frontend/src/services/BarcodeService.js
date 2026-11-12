import { BASE_URL, getAuthHeaders, handleResponse } from '@/services/api.js';

// Codes are sent as typed or scanned: the server normalizes them (a 12-digit
// UPC-A gets a leading 0) and validates the check digit, so the frontend never
// does. A code is untrusted input, hence encodeURIComponent in the path.

export async function getItemByCode(code) {
    const response = await fetch(`${BASE_URL}/items/by-code/${encodeURIComponent(code)}`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

export async function linkCode(itemId, code) {
    const response = await fetch(`${BASE_URL}/items/${itemId}/codes`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ code })
    });
    return handleResponse(response);
}

export async function unlinkCode(itemId, code) {
    const response = await fetch(`${BASE_URL}/items/${itemId}/codes/${encodeURIComponent(code)}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

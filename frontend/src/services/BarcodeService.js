import { BASE_URL, getAuthHeaders, handleResponse } from '@/services/api.js';

// Codes are sent as typed or scanned: the server normalizes them (a 12-digit
// UPC-A gets a leading 0) and validates the check digit, so the frontend never
// does. A code is untrusted input, hence encodeURIComponent in the path.

// Only digits go into the lookup path. encodeURIComponent leaves dots alone,
// and URL parsing turns ".." (or "%2E%2E") into "go up a level", so a typed
// ".." would call GET /items/ instead. Anything that isn't all digits is
// rejected here as the server would (422) without a request. This is
// validation, not normalization: the length and check digit stay the
// server's job.
function invalidCodeError() {
    const err = new Error('Code must be a 12-digit UPC-A or 13-digit EAN-13');
    err.status = 422;
    return err;
}

export async function getItemByCode(code) {
    if (!/^\d+$/.test(code)) throw invalidCodeError();
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

// code comes from item.codes (always 13 digits); guarded like the lookup so
// no code ever reaches a path unchecked.
export async function unlinkCode(itemId, code) {
    if (!/^\d+$/.test(code)) throw invalidCodeError();
    const response = await fetch(`${BASE_URL}/items/${itemId}/codes/${encodeURIComponent(code)}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
}

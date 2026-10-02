export const BASE_URL = import.meta.env.VITE_API_URL

export function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
    };
}

export function getPublicHeaders() {
    return {
        'Content-Type': 'application/json'
    };
}

export function errorMessageFrom(detail, fallback = 'Request failed.') {
    // FastAPI validation errors (422) carry a list of objects, not a string.
    if (Array.isArray(detail)) return detail[0]?.msg?.replace(/^Value error, /, '') ?? fallback;
    return detail ?? fallback;
}

export async function handleResponse(response) {
    if (response.status === 401) {
        const err = new Error('Session expired. Please log in again.');
        err.status = 401;
        throw err;
    }
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const err = new Error(errorMessageFrom(data.detail));
        err.status = response.status;
        throw err;
    }
    if (response.status === 204) return null;
    return response.json();
}

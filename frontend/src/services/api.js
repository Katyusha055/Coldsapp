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

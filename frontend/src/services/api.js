export const BASE_URL = 'https://coldsapp.up.railway.app';

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

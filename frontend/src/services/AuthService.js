import { BASE_URL, getPublicHeaders } from './api.js';
import { useContactsStore } from '@/stores/contacts.js';

export async function register(name, phone, password) {
    const response = await fetch(`${BASE_URL}/auth/register`, {
        method: 'POST',
        headers: getPublicHeaders(),
        body: JSON.stringify({ name, phone, password })
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail ?? 'Registration failed.');
    }
    return response.json();
}

export async function login(phone, password) {
    const body = new URLSearchParams({ username: phone, password });
    const response = await fetch(`${BASE_URL}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString()
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail ?? 'Login failed.');
    }
    return response.json();
}

export function saveToken(access_token) {
    localStorage.setItem('access_token', access_token);
}

export function getToken() {
    return localStorage.getItem('access_token');
}

export function removeToken() {
    localStorage.removeItem('access_token');
}

export function resetStores() {
    useContactsStore().$reset();
}

export function logout() {
    removeToken();
    resetStores();
}

import AppLayout from '@/layout/AppLayout.vue';
import { getToken } from '@/services/AuthService.js';
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: AppLayout,
            meta: { requiresAuth: true },
            children: [
                {
                    path: '/',
                    name: 'dashboard',
                    component: () => import('@/views/Dashboard.vue')
                },
                {
                    path: '/clients',
                    name: 'clients',
                    component: () => import('@/views/Clients.vue')
                },
                {
                    path: '/tickets',
                    name: 'tickets',
                    component: () => import('@/views/Tickets.vue')
                },
                {
                    path: '/whatsapp',
                    name: 'whatsapp',
                    component: () => import('@/views/Whatsapp.vue')
                },
                {
                    path: '/contacts',
                    name: 'contacts',
                    component: () => import('@/views/Contacts.vue')
                }
            ]
        },
        {
            path: '/auth/login',
            name: 'login',
            component: () => import('@/views/pages/auth/Login.vue')
        },
        {
            path: '/auth/register',
            name: 'register',
            component: () => import('@/views/pages/auth/Register.vue')
        },
        {
            path: '/auth/access',
            name: 'accessDenied',
            component: () => import('@/views/pages/auth/Access.vue')
        },
        {
            path: '/auth/error',
            name: 'error',
            component: () => import('@/views/pages/auth/Error.vue')
        },
        {
            path: '/:pathMatch(.*)*',
            name: 'notFound',
            component: () => import('@/views/pages/NotFound.vue')
        }
    ]
});

router.beforeEach((to) => {
    const token = getToken();
    if (to.meta.requiresAuth && !token) {
        return { path: '/auth/login' };
    }
    if (!to.meta.requiresAuth && token) {
        return { path: '/' };
    }
});

export default router;

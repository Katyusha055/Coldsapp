<script setup>
import { useLayout } from '@/layout/composables/layout';
import { computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { hasTouchScreen } from '@/utils/device.js';
// import AppFooter from './AppFooter.vue';
import AppSidebar from './AppSidebar.vue';
import AppTopbar from './AppTopbar.vue';

const { layoutConfig, layoutState, hideMobileMenu } = useLayout();
const route = useRoute();
const router = useRouter();
const toast = useToast();

// On a phone, once per session, a toast offers the scanner: the one part of
// the app built for a phone. The "shown" flag is a UI flag in sessionStorage,
// not client data, and lasts until the tab is closed. If storage is
// unavailable, the toast is skipped rather than shown on every load.
const SCAN_SHORTCUT_GROUP = 'scan-shortcut';
const SCAN_SHORTCUT_SHOWN_KEY = 'scanShortcutShown';

onMounted(() => {
    if (!hasTouchScreen() || route.name === 'inventoryScan') return;
    try {
        if (sessionStorage.getItem(SCAN_SHORTCUT_SHOWN_KEY)) return;
        sessionStorage.setItem(SCAN_SHORTCUT_SHOWN_KEY, '1');
    } catch {
        return;
    }
    toast.add({ group: SCAN_SHORTCUT_GROUP, severity: 'info', summary: '¿Vas a escanear un código?', detail: 'Toca aquí para abrir el escáner.', life: 10000 });
});

function openScannerFromToast() {
    toast.removeGroup(SCAN_SHORTCUT_GROUP);
    router.push({ name: 'inventoryScan' });
}

const containerClass = computed(() => {
    return {
        'layout-overlay': layoutConfig.menuMode === 'overlay',
        'layout-static': layoutConfig.menuMode === 'static',
        'layout-overlay-active': layoutState.overlayMenuActive,
        'layout-mobile-active': layoutState.mobileMenuActive,
        'layout-static-inactive': layoutState.staticMenuInactive
    };
});
</script>

<template>
    <div class="layout-wrapper" :class="containerClass">
        <AppTopbar />
        <AppSidebar />
        <div class="layout-main-container">
            <div class="layout-main">
                <router-view />
            </div>
            <!-- <AppFooter /> -->
        </div>
        <div class="layout-mask animate-fadein" @click="hideMobileMenu" />
    </div>
    <Toast />
    <Toast :group="SCAN_SHORTCUT_GROUP" position="bottom-center">
        <template #message="{ message }">
            <div class="flex flex-col gap-2 w-full cursor-pointer" @click="openScannerFromToast">
                <span class="font-semibold">{{ message.summary }}</span>
                <span>{{ message.detail }}</span>
                <Button label="Abrir escáner" icon="pi pi-camera" size="small" class="self-start" />
            </div>
        </template>
    </Toast>
</template>

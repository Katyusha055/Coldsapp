<script setup>
import { ref } from 'vue';
import AppMenuItem from './AppMenuItem.vue';

const model = ref([
    {
        label: 'Inicio',
        items: [
            {
                label: 'Panel',
                icon: 'pi pi-fw pi-home',
                to: '/'
            }
        ]
    },
    {
        label: 'Gestión',
        items: [
            {
                label: 'Clientes',
                icon: 'pi pi-fw pi-users',
                to: '/clients'
            },
            {
                label: 'Tickets',
                icon: 'pi pi-fw pi-ticket',
                to: '/tickets'
            },
            {
                label: 'WhatsApp',
                icon: 'pi pi-fw pi-whatsapp',
                to: '/whatsapp'
            },
            {
                label: 'Contactos',
                icon: 'pi pi-fw pi-address-book',
                to: '/contacts'
            }
        ]
    }
]);
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="item">
            <app-menu-item v-if="!item.separator" :item="item" :index="i"></app-menu-item>
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>

<style lang="scss" scoped></style>

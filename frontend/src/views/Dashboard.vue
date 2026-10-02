<script setup>
import { ref, computed, onMounted } from 'vue';
import { useClientsStore } from '@/stores/clients.js';
import { useTicketsStore } from '@/stores/tickets.js';
import PendingWhatsappWidget from '@/components/dashboard/PendingWhatsappWidget.vue';
import TopClientsWidget from '@/components/dashboard/TopClientsWidget.vue';
import PendingTicketsWidget from '@/components/dashboard/PendingTicketsWidget.vue';

const clientsStore = useClientsStore();
const ticketsStore = useTicketsStore();
const settled = ref(false);

function totalOf(store) {
    if (store.loaded) return store.items.length;
    return settled.value ? 0 : null;
}

const totalClients = computed(() => totalOf(clientsStore));
const totalTickets = computed(() => totalOf(ticketsStore));

onMounted(async () => {
    await Promise.allSettled([clientsStore.load(), ticketsStore.load()]);
    settled.value = true;
});
</script>

<template>
    <div class="grid grid-cols-12 gap-8">

        <!-- Summary banner -->
        <div class="col-span-12">
            <div
                class="relative overflow-hidden rounded-2xl min-h-[25vh] flex items-center px-12 py-8"
                style="background: linear-gradient(135deg, var(--p-primary-700, #1d4ed8) 0%, var(--p-primary-500, #3b82f6) 55%, #06b6d4 100%)"
            >
                <!-- Decorative blobs -->
                <div
                    class="absolute -top-10 -right-10 w-60 h-60 rounded-full pointer-events-none"
                    style="background: rgba(255,255,255,0.08)"
                ></div>
                <div
                    class="absolute bottom-[-3rem] left-[-2rem] w-80 h-80 rounded-full pointer-events-none"
                    style="background: rgba(255,255,255,0.05)"
                ></div>
                <div
                    class="absolute top-4 left-1/2 w-40 h-40 rounded-full pointer-events-none"
                    style="background: rgba(255,255,255,0.04)"
                ></div>

                <!-- Content -->
                <div class="relative z-10 flex flex-col gap-6 text-white w-full">
                    <div>
                        <p class="text-2xl font-semibold">¡Bienvenido de vuelta!</p>
                        <p class="text-base" style="opacity: 0.7">Aquí tienes un resumen rápido de tu espacio de trabajo.</p>
                    </div>

                    <div class="flex items-center gap-12">
                        <div class="flex flex-col gap-0.5">
                            <span class="text-4xl font-bold tracking-tight">
                                {{ totalClients ?? '—' }}
                            </span>
                            <span class="text-sm font-medium" style="opacity: 0.75">Total de Clientes</span>
                        </div>

                        <div class="self-stretch w-px" style="background: rgba(255,255,255,0.25)"></div>

                        <div class="flex flex-col gap-0.5">
                            <span class="text-4xl font-bold tracking-tight">
                                {{ totalTickets ?? '—' }}
                            </span>
                            <span class="text-sm font-medium" style="opacity: 0.75">Total de Tickets</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Widgets -->
        <div class="col-span-12 xl:col-span-4">
            <PendingWhatsappWidget />
        </div>
        <div class="col-span-12 xl:col-span-4">
            <TopClientsWidget />
        </div>
        <div class="col-span-12 xl:col-span-4">
            <PendingTicketsWidget />
        </div>

    </div>
</template>

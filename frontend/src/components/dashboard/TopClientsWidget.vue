<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useClientsStore } from '@/stores/clients.js';
import { useTicketsStore } from '@/stores/tickets.js';

const router = useRouter();
const clientsStore = useClientsStore();
const ticketsStore = useTicketsStore();
const loading = ref(true);

const INACTIVE_STATUSES = new Set(['cancelled', 'delivered']);

const topClients = computed(() => {
    const ticketCounts = {};
    for (const ticket of ticketsStore.items) {
        if (!INACTIVE_STATUSES.has(ticket.status)) {
            ticketCounts[ticket.client_id] = (ticketCounts[ticket.client_id] ?? 0) + 1;
        }
    }

    return clientsStore.items
        .map((c) => ({ ...c, activeCount: ticketCounts[c.id] ?? 0 }))
        .sort((a, b) => b.activeCount - a.activeCount)
        .slice(0, 3);
});

onMounted(async () => {
    try {
        await Promise.all([clientsStore.load(), ticketsStore.load()]);
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <Card>
        <template #title>Clientes Más Activos</template>
        <template #content>
            <div v-if="loading" class="flex justify-center py-4">
                <ProgressSpinner style="width: 40px; height: 40px" />
            </div>
            <div v-else-if="topClients.length === 0" class="text-muted-color text-center py-4">
                Sin datos disponibles
            </div>
            <div v-else class="flex flex-col gap-2">
                <div
                    v-for="client in topClients"
                    :key="client.id"
                    class="flex items-center justify-between p-3 border border-surface rounded cursor-pointer hover:bg-emphasis transition-colors"
                    @click="router.push('/clients')"
                >
                    <div class="flex flex-col gap-1">
                        <span class="font-semibold">{{ client.name }}</span>
                        <span class="text-sm text-muted-color">{{ client.phone }}</span>
                    </div>
                    <Badge :value="client.activeCount" severity="info" />
                </div>
            </div>
        </template>
    </Card>
</template>

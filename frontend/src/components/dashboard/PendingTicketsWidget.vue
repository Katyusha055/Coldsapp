<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useTicketsStore } from '@/stores/tickets.js';

const router = useRouter();
const ticketsStore = useTicketsStore();
const loading = ref(true);

const pendingTickets = computed(() =>
    ticketsStore.items
        .filter((t) => t.status === 'pending')
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 3)
);

function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

onMounted(async () => {
    try {
        await ticketsStore.load();
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <Card>
        <template #title>Tickets Pendientes Nuevos</template>
        <template #content>
            <div v-if="loading" class="flex justify-center py-4">
                <ProgressSpinner style="width: 40px; height: 40px" />
            </div>
            <div v-else-if="pendingTickets.length === 0" class="text-muted-color text-center py-4">
                Sin tickets pendientes
            </div>
            <div v-else class="flex flex-col gap-2">
                <div
                    v-for="ticket in pendingTickets"
                    :key="ticket.id"
                    class="flex items-center justify-between p-3 border border-surface rounded cursor-pointer hover:bg-emphasis transition-colors"
                    @click="router.push('/tickets')"
                >
                    <span class="font-semibold truncate max-w-xs">{{ ticket.title }}</span>
                    <span class="text-sm text-muted-color whitespace-nowrap ml-4">{{ formatDate(ticket.created_at) }}</span>
                </div>
            </div>
        </template>
    </Card>
</template>

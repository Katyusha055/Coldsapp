<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { handleAuthError } from '@/services/AuthService.js';
import { useInventoryStore } from '@/stores/inventory.js';

const router = useRouter();
const inventoryStore = useInventoryStore();
const loading = ref(true);
const loadFailed = ref(false);

const alertCount = computed(() => inventoryStore.alertItems.length);

onMounted(async () => {
    try {
        await inventoryStore.load();
    } catch (err) {
        if (handleAuthError(err)) return;
        // Without this, an empty store would read as "no alerts".
        loadFailed.value = true;
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <Card>
        <template #title>Alertas de Inventario</template>
        <template #content>
            <div v-if="loading" class="flex justify-center py-4">
                <ProgressSpinner style="width: 40px; height: 40px" />
            </div>
            <div v-else-if="loadFailed" class="text-red-500 text-center py-4">No se pudieron cargar las alertas de inventario.</div>
            <div v-else class="flex items-center justify-between p-3 border border-surface rounded cursor-pointer hover:bg-emphasis transition-colors" @click="router.push({ path: '/inventory', query: { alerts: '1' } })">
                <span v-if="alertCount === 0" class="text-muted-color">Sin alertas de inventario</span>
                <span v-else class="font-semibold">Tienes {{ alertCount }} {{ alertCount === 1 ? 'alerta' : 'alertas' }} de inventario</span>
                <i class="pi pi-exclamation-triangle" :class="alertCount === 0 ? 'text-muted-color' : 'text-red-500'" />
            </div>
        </template>
    </Card>
</template>

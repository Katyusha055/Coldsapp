<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePendingsStore } from '@/stores/pendings.js';

const router = useRouter();
const pendingsStore = usePendingsStore();
const loading = ref(true);
const failed = ref(false);

const pendingContacts = computed(() => (failed.value ? [] : pendingsStore.items));

onMounted(async () => {
    try {
        // Forced: new pendings only reach the store live on the WhatsApp page.
        await pendingsStore.load(true);
    } catch {
        failed.value = true;
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <Card>
        <template #title>
            <div class="flex items-center justify-between">
                <span>Contactos pendientes de WhatsApp</span>
                <Badge v-if="!loading" :value="pendingContacts.length" :severity="pendingContacts.length > 0 ? 'info' : 'secondary'" />
            </div>
        </template>
        <template #content>
            <div v-if="loading" class="flex justify-center py-4">
                <ProgressSpinner style="width: 40px; height: 40px" />
            </div>
            <div v-else class="cursor-pointer" @click="router.push('/whatsapp')">
                <div v-if="pendingContacts.length === 0" class="text-muted-color text-center py-4">
                    Sin contactos pendientes
                </div>
                <div v-else class="flex items-center justify-between p-3 border border-surface rounded hover:bg-emphasis transition-colors">
                    <span class="font-semibold">{{ pendingContacts.length }} contacto(s) esperando revisión</span>
                    <i class="pi pi-arrow-right text-muted-color" />
                </div>
            </div>
        </template>
    </Card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import { handleAuthError } from '@/services/AuthService.js';
import { useContactsStore } from '@/stores/contacts.js';

const toast = useToast();
const store = useContactsStore();

const loadError = ref('');

const drawerVisible = ref(false);
const selectedContact = ref(null);
const editableName = ref('');

const searchQuery = ref('');
const tableFirst = ref(0);

watch(searchQuery, () => {
    tableFirst.value = 0;
});

const filteredContacts = computed(() => {
    const query = searchQuery.value.trim().toLowerCase();
    if (!query) return store.activeContacts;
    return store.activeContacts.filter((contact) => contact.name?.toLowerCase().includes(query));
});

const isNameDirty = computed(() => {
    if (!selectedContact.value) return false;
    return editableName.value.trim() !== (selectedContact.value.name ?? '');
});

function formatDate(value) {
    if (!value) return '';
    return new Date(value).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatPhone(remoteJid) {
    if (!remoteJid) return '';
    return `+${remoteJid.split('@')[0]}`;
}

function errorMessageFor(err) {
    if (err.status === 404) return 'No se encontró una instancia de WhatsApp vinculada a tu cuenta.';
    if (err.status === 409) return 'La instancia de WhatsApp no está conectada. Conéctala desde la sección de WhatsApp e intenta de nuevo.';
    return err.message ?? 'Ocurrió un error inesperado.';
}

function handleError(err) {
    if (handleAuthError(err)) return;
    toast.add({ severity: 'error', summary: 'Error', detail: errorMessageFor(err), life: 3000 });
}

onMounted(async () => {
    try {
        await store.loadContacts();
    } catch (err) {
        if (handleAuthError(err)) return;
        loadError.value = errorMessageFor(err);
    }
});

async function onRefresh() {
    try {
        await store.refresh();
        toast.add({ severity: 'success', summary: 'Actualizado', detail: 'Contactos actualizados correctamente.', life: 3000 });
    } catch (err) {
        handleError(err);
    }
}

function onRowClick(event) {
    selectedContact.value = event.data;
    editableName.value = event.data.name ?? '';
    drawerVisible.value = true;
}

async function saveName() {
    if (!selectedContact.value || !isNameDirty.value) return;
    try {
        await store.updateName(selectedContact.value.id, editableName.value.trim());
        toast.add({ severity: 'success', summary: 'Guardado', detail: 'Nombre actualizado correctamente.', life: 3000 });
    } catch (err) {
        handleError(err);
    }
}

async function onToggleOptedOut(contact, value) {
    try {
        await store.toggleOptedOut(contact.id, value);
    } catch (err) {
        handleError(err);
    }
}
</script>

<template>
    <div>
        <div class="card mb-6">
            <div class="flex items-center justify-between flex-wrap gap-4">
                <h4 class="m-0">Contactos</h4>
                <Button label="Actualizar" icon="pi pi-refresh" :loading="store.loading" @click="onRefresh" />
            </div>
            <small v-if="loadError" class="text-red-500 block mt-3">{{ loadError }}</small>
        </div>

        <div class="card">
            <DataTable :value="filteredContacts" dataKey="id" :rowClass="() => 'cursor-pointer'" @row-click="onRowClick" paginator :rows="30" v-model:first="tableFirst" rowHover>
                <template #header>
                    <div class="flex items-center justify-between flex-wrap gap-4">
                        <h4 class="m-0">Contactos Activos</h4>
                        <InputText v-model="searchQuery" placeholder="Buscar por nombre..." />
                    </div>
                </template>

                <Column field="name" header="Nombre" sortable style="min-width: 14rem">
                    <template #body="slotProps">
                        <span v-if="slotProps.data.name">{{ slotProps.data.name }}</span>
                        <span v-else class="italic text-surface-500">Sin Nombre</span>
                    </template>
                </Column>
                <Column field="remote_jid" header="Número" sortable style="min-width: 12rem">
                    <template #body="slotProps">
                        {{ formatPhone(slotProps.data.remote_jid) }}
                    </template>
                </Column>
                <Column field="last_incoming_at" header="Último Mensaje Recibido" sortable style="min-width: 16rem">
                    <template #body="slotProps">
                        {{ formatDate(slotProps.data.last_incoming_at) || '—' }}
                    </template>
                </Column>
                <Column field="last_broadcast_at" header="Última Campaña" sortable style="min-width: 14rem">
                    <template #body="slotProps">
                        {{ formatDate(slotProps.data.last_broadcast_at) || '—' }}
                    </template>
                </Column>
                <Column field="created_at" header="Fecha de Creación" sortable style="min-width: 14rem">
                    <template #body="slotProps">
                        {{ formatDate(slotProps.data.created_at) }}
                    </template>
                </Column>
                <Column field="opted_out" header="Dado de Baja" style="min-width: 8rem">
                    <template #body="slotProps">
                        <div @click.stop>
                            <Checkbox binary :modelValue="slotProps.data.opted_out" @update:modelValue="(value) => onToggleOptedOut(slotProps.data, value)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <Toast />

        <!-- Contact Detail Drawer -->
        <Drawer v-model:visible="drawerVisible" position="right" :style="{ width: '28rem' }" header="Detalle del Contacto">
            <div v-if="selectedContact" class="flex flex-col gap-6">
                <div>
                    <label for="contact-name" class="block font-bold mb-3">Nombre</label>
                    <InputText id="contact-name" v-model="editableName" placeholder="Sin nombre" fluid @keyup.enter="saveName" />
                    <Button label="Guardar" icon="pi pi-check" class="mt-3" :disabled="!isNameDirty" @click="saveName" />
                </div>

                <div>
                    <label class="block font-bold mb-3">Número</label>
                    <span>{{ formatPhone(selectedContact.remote_jid) }}</span>
                </div>

                <div class="flex items-center gap-2">
                    <Checkbox inputId="contact-opted-out" binary :modelValue="selectedContact.opted_out" @update:modelValue="(value) => onToggleOptedOut(selectedContact, value)" />
                    <label for="contact-opted-out">Dado de baja</label>
                </div>
                <small class="text-surface-500 -mt-4">Los contactos dados de baja no reciben campañas de difusión.</small>

                <div>
                    <label class="block font-bold mb-3">Último Mensaje Recibido</label>
                    <span>{{ formatDate(selectedContact.last_incoming_at) || '—' }}</span>
                </div>
                <div>
                    <label class="block font-bold mb-3">Última Campaña Enviada</label>
                    <span>{{ formatDate(selectedContact.last_broadcast_at) || '—' }}</span>
                </div>
                <div>
                    <label class="block font-bold mb-3">Fecha de Creación</label>
                    <span>{{ formatDate(selectedContact.created_at) }}</span>
                </div>
            </div>
        </Drawer>
    </div>
</template>

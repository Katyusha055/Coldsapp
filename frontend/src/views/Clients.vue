<script setup>
import { ref, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { handleAuthError } from '@/services/AuthService.js';
import { useClientsStore } from '@/stores/clients.js';
import { useTicketsStore } from '@/stores/tickets.js';
import { useDrawerNavigation } from '@/composables/useDrawerNavigation.js';
import EntityDrawer from '@/components/EntityDrawer.vue';
import PlaceholderCell from '@/components/PlaceholderCell.vue';
import { formatDate } from '@/utils/format.js';

const router = useRouter();
const toast = useToast();
const clientsStore = useClientsStore();
const ticketsStore = useTicketsStore();

const expandedRows = ref({});
const deleteClientDialog = ref(false);
const client = ref({});
const clientToDelete = ref({});
const nav = useDrawerNavigation(() => clientsStore.items);

watch(
    () => [nav.currentId, nav.visible],
    () => {
        client.value = nav.isNew ? {} : { ...clientsStore.byId(nav.currentId) };
        submitted.value = false;
        errorMessage.value = '';
    }
);
const submitted = ref(false);
const errorMessage = ref('');
const loadError = ref('');

function handleError(err) {
    if (handleAuthError(err)) return;
    errorMessage.value = err.message ?? 'An unexpected error occurred.';
}

onMounted(async () => {
    try {
        await Promise.all([clientsStore.load(), ticketsStore.load()]);
    } catch (err) {
        if (handleAuthError(err)) return;
        loadError.value = err.message ?? 'Failed to load clients.';
    }
});

function clientTickets(clientId) {
    return ticketsStore.items.filter((t) => t.client_id === clientId);
}

function toggleRow(row) {
    if (row.id in expandedRows.value) {
        const updated = { ...expandedRows.value };
        delete updated[row.id];
        expandedRows.value = updated;
    } else {
        expandedRows.value = { ...expandedRows.value, [row.id]: row };
    }
}


async function saveClient() {
    submitted.value = true;
    errorMessage.value = '';

    if (!client.value.name?.trim() || !client.value.phone?.trim()) return;

    try {
        if (client.value.id) {
            const payload = { name: client.value.name.trim(), phone: client.value.phone.trim() };
            if (client.value.description) payload.description = client.value.description;
            await clientsStore.update(client.value.id, payload);
            submitted.value = false;
            toast.add({ severity: 'success', summary: 'Actualizado', detail: 'Cliente actualizado correctamente.', life: 3000 });
        } else {
            const payload = { name: client.value.name.trim(), phone: client.value.phone.trim() };
            if (client.value.description) payload.description = client.value.description;
            await clientsStore.create(payload);
            toast.add({ severity: 'success', summary: 'Creado', detail: 'Cliente creado correctamente.', life: 3000 });
            nav.close();
        }
    } catch (err) {
        handleError(err);
    }
}

function confirmDeleteClient(c) {
    clientToDelete.value = c;
    errorMessage.value = '';
    deleteClientDialog.value = true;
}

async function doDeleteClient() {
    try {
        await clientsStore.remove(clientToDelete.value.id);
        ticketsStore.invalidate();
        deleteClientDialog.value = false;
        clientToDelete.value = {};
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Cliente eliminado correctamente.', life: 3000 });
    } catch (err) {
        deleteClientDialog.value = false;
        handleError(err);
    }
}
</script>

<template>
    <div>
        <div class="card">
            <Toolbar class="mb-6">
                <template #start>
                    <Button label="Nuevo Cliente" icon="pi pi-plus" severity="secondary" @click="nav.openNew()" />
                </template>
            </Toolbar>

            <small v-if="loadError" class="text-red-500 block mb-4">{{ loadError }}</small>

            <DataTable :ref="nav.bindTable" :value="clientsStore.items" dataKey="id" v-model:expandedRows="expandedRows">
                <template #header>
                    <div class="flex items-center justify-between">
                        <h4 class="m-0">Clientes</h4>
                    </div>
                </template>

                <Column style="width: 3rem">
                    <template #body="slotProps">
                        <Button
                            :icon="slotProps.data.id in expandedRows ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"
                            text
                            rounded
                            size="small"
                            v-tooltip.top="'Ver tickets'"
                            @click="toggleRow(slotProps.data)"
                        />
                    </template>
                </Column>
                <Column field="name" header="Nombre" sortable style="min-width: 16rem"></Column>
                <Column field="phone" header="Teléfono" sortable style="min-width: 12rem"></Column>
                <Column field="description" header="Descripción" style="min-width: 20rem; max-width: 20rem">
                    <template #body="slotProps">
                        <PlaceholderCell :value="slotProps.data.description" placeholder="Sin descripción" truncate />
                    </template>
                </Column>
                <Column field="created_at" header="Fecha de Creación" sortable style="min-width: 14rem">
                    <template #body="slotProps">
                        {{ formatDate(slotProps.data.created_at) }}
                    </template>
                </Column>
                <Column :exportable="false" style="min-width: 8rem">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" outlined rounded class="mr-2" @click="nav.open(slotProps.data.id)" />
                        <Button icon="pi pi-trash" outlined rounded severity="danger" @click="confirmDeleteClient(slotProps.data)" />
                    </template>
                </Column>

                <template #expansion="slotProps">
                    <div class="p-4">
                        <DataTable
                            :value="clientTickets(slotProps.data.id)"
                            dataKey="id"
                            emptyMessage="No se encontraron tickets."
                            :rowClass="() => 'cursor-pointer'"
                            @row-click="() => router.push('/tickets')"
                        >
                            <Column field="title" header="Título" style="min-width: 16rem"></Column>
                            <Column field="status" header="Estado" style="min-width: 10rem"></Column>
                            <Column field="created_at" header="Fecha de Creación" style="min-width: 14rem">
                                <template #body="ticketSlot">
                                    {{ formatDate(ticketSlot.data.created_at) }}
                                </template>
                            </Column>
                        </DataTable>
                    </div>
                </template>
            </DataTable>
        </div>

        <Toast />

        <!-- Create / Edit Drawer -->
        <EntityDrawer :nav="nav" :header="nav.isNew ? 'Nuevo Cliente' : 'Editar Cliente'">
            <div class="flex flex-col gap-6">
                <div>
                    <label for="client-name" class="block font-bold mb-3">Nombre</label>
                    <InputText id="client-name" v-model.trim="client.name" autofocus :invalid="submitted && !client.name" fluid />
                    <small v-if="submitted && !client.name" class="text-red-500">El nombre es requerido.</small>
                </div>
                <div>
                    <label for="client-phone" class="block font-bold mb-3">Teléfono</label>
                    <InputText id="client-phone" v-model.trim="client.phone" :invalid="submitted && !client.phone" fluid />
                    <small v-if="submitted && !client.phone" class="text-red-500">El teléfono es requerido.</small>
                </div>
                <div>
                    <label for="client-description" class="block font-bold mb-3">Descripción</label>
                    <Textarea id="client-description" v-model="client.description" rows="3" fluid />
                </div>
                <small v-if="errorMessage" class="text-red-500">{{ errorMessage }}</small>
            </div>
            <template #footer>
                <div class="flex justify-end gap-2">
                    <Button label="Cancelar" icon="pi pi-times" text @click="nav.close()" />
                    <Button label="Guardar" icon="pi pi-check" @click="saveClient" />
                </div>
            </template>
        </EntityDrawer>

        <!-- Delete Confirmation Dialog -->
        <Dialog v-model:visible="deleteClientDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle text-3xl!" />
                <span v-if="clientToDelete">¿Estás seguro de que deseas eliminar a <b>{{ clientToDelete.name }}</b>?</span>
            </div>
            <template #footer>
                <Button label="No" icon="pi pi-times" text @click="deleteClientDialog = false" />
                <Button label="Sí" icon="pi pi-check" severity="danger" @click="doDeleteClient" />
            </template>
        </Dialog>
    </div>
</template>

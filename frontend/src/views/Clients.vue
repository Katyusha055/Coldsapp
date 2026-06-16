<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { removeToken } from '@/services/AuthService.js';
import { getClients, createClient, updateClient, deleteClient } from '@/services/ClientService.js';

const router = useRouter();
const toast = useToast();

const clients = ref([]);
const clientDialog = ref(false);
const deleteClientDialog = ref(false);
const client = ref({});
const submitted = ref(false);
const errorMessage = ref('');
const loadError = ref('');

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

function handleError(err) {
    if (err.status === 401) {
        removeToken();
        toast.add({ severity: 'warn', summary: 'Session Expired', detail: 'Please log in again.', life: 4000 });
        router.push('/auth/login');
        return;
    }
    errorMessage.value = err.message ?? 'An unexpected error occurred.';
}

onMounted(async () => {
    try {
        clients.value = await getClients();
    } catch (err) {
        if (err.status === 401) {
            handleError(err);
        } else {
            loadError.value = err.message ?? 'Failed to load clients.';
        }
    }
});

function openNew() {
    client.value = {};
    submitted.value = false;
    errorMessage.value = '';
    clientDialog.value = true;
}

function editClient(c) {
    client.value = { ...c };
    submitted.value = false;
    errorMessage.value = '';
    clientDialog.value = true;
}

function hideDialog() {
    clientDialog.value = false;
    submitted.value = false;
    errorMessage.value = '';
}

async function saveClient() {
    submitted.value = true;
    errorMessage.value = '';

    if (!client.value.name?.trim() || !client.value.phone?.trim()) return;

    try {
        if (client.value.id) {
            const payload = { name: client.value.name.trim(), phone: client.value.phone.trim() };
            if (client.value.description) payload.description = client.value.description;
            const updated = await updateClient(client.value.id, payload);
            const idx = clients.value.findIndex((c) => c.id === client.value.id);
            if (idx !== -1) clients.value[idx] = updated;
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Client updated successfully.', life: 3000 });
        } else {
            const payload = { name: client.value.name.trim(), phone: client.value.phone.trim() };
            if (client.value.description) payload.description = client.value.description;
            const created = await createClient(payload);
            clients.value.push(created);
            toast.add({ severity: 'success', summary: 'Created', detail: 'Client created successfully.', life: 3000 });
        }
        clientDialog.value = false;
        client.value = {};
    } catch (err) {
        handleError(err);
    }
}

function confirmDeleteClient(c) {
    client.value = c;
    errorMessage.value = '';
    deleteClientDialog.value = true;
}

async function doDeleteClient() {
    try {
        await deleteClient(client.value.id);
        clients.value = clients.value.filter((c) => c.id !== client.value.id);
        deleteClientDialog.value = false;
        client.value = {};
        toast.add({ severity: 'success', summary: 'Deleted', detail: 'Client deleted successfully.', life: 3000 });
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
                    <Button label="New Client" icon="pi pi-plus" severity="secondary" @click="openNew" />
                </template>
            </Toolbar>

            <small v-if="loadError" class="text-red-500 block mb-4">{{ loadError }}</small>

            <DataTable :value="clients" dataKey="id">
                <template #header>
                    <div class="flex items-center justify-between">
                        <h4 class="m-0">Clients</h4>
                    </div>
                </template>

                <Column field="name" header="Name" sortable style="min-width: 16rem"></Column>
                <Column field="phone" header="Phone" sortable style="min-width: 12rem"></Column>
                <Column field="description" header="Description" style="min-width: 20rem"></Column>
                <Column field="created_at" header="Created At" sortable style="min-width: 14rem">
                    <template #body="slotProps">
                        {{ formatDate(slotProps.data.created_at) }}
                    </template>
                </Column>
                <Column :exportable="false" style="min-width: 8rem">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" outlined rounded class="mr-2" @click="editClient(slotProps.data)" />
                        <Button icon="pi pi-trash" outlined rounded severity="danger" @click="confirmDeleteClient(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>
        </div>

        <Toast />

        <!-- Create / Edit Dialog -->
        <Dialog v-model:visible="clientDialog" :style="{ width: '450px' }" :header="client.id ? 'Edit Client' : 'New Client'" :modal="true">
            <div class="flex flex-col gap-6">
                <div>
                    <label for="client-name" class="block font-bold mb-3">Name</label>
                    <InputText id="client-name" v-model.trim="client.name" autofocus :invalid="submitted && !client.name" fluid />
                    <small v-if="submitted && !client.name" class="text-red-500">Name is required.</small>
                </div>
                <div>
                    <label for="client-phone" class="block font-bold mb-3">Phone</label>
                    <InputText id="client-phone" v-model.trim="client.phone" :invalid="submitted && !client.phone" fluid />
                    <small v-if="submitted && !client.phone" class="text-red-500">Phone is required.</small>
                </div>
                <div>
                    <label for="client-description" class="block font-bold mb-3">Description</label>
                    <Textarea id="client-description" v-model="client.description" rows="3" fluid />
                </div>
                <small v-if="errorMessage" class="text-red-500">{{ errorMessage }}</small>
            </div>
            <template #footer>
                <Button label="Cancel" icon="pi pi-times" text @click="hideDialog" />
                <Button label="Save" icon="pi pi-check" @click="saveClient" />
            </template>
        </Dialog>

        <!-- Delete Confirmation Dialog -->
        <Dialog v-model:visible="deleteClientDialog" :style="{ width: '450px' }" header="Confirm" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle text-3xl!" />
                <span v-if="client">Are you sure you want to delete <b>{{ client.name }}</b>?</span>
            </div>
            <template #footer>
                <Button label="No" icon="pi pi-times" text @click="deleteClientDialog = false" />
                <Button label="Yes" icon="pi pi-check" severity="danger" @click="doDeleteClient" />
            </template>
        </Dialog>
    </div>
</template>

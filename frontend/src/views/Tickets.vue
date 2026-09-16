<script setup>
import { ref, computed, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { handleAuthError } from '@/services/AuthService.js';
import { getTickets, createTicket, updateTicket, updateTicketStatus, deleteTicket } from '@/services/TicketService.js';
import { getClients } from '@/services/ClientService.js';

const VALID_TRANSITIONS = {
    pending:     ['in_progress', 'cancelled'],
    in_progress: ['ready', 'cancelled'],
    ready:       ['delivered', 'cancelled'],
    delivered:   [],
    cancelled:   []
};

const toast = useToast();

const tickets = ref([]);
const clients = ref([]);
const ticketDialog = ref(false);
const deleteTicketDialog = ref(false);
const ticket = ref({});
const submitted = ref(false);
const errorMessage = ref('');
const loadError = ref('');
const filterStatus = ref('all');

const filterStatusOptions = [
    { label: 'Todos', value: 'all' },
    { label: 'Pendiente', value: 'pending' },
    { label: 'En progreso', value: 'in_progress' },
    { label: 'Listo', value: 'ready' },
    { label: 'Entregado', value: 'delivered' },
    { label: 'Cancelado', value: 'cancelled' }
];

const filteredTickets = computed(() => {
    if (filterStatus.value === 'all') return tickets.value;
    return tickets.value.filter((t) => t.status === filterStatus.value);
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

function statusLabel(status) {
    const labels = {
        pending: 'Pendiente',
        in_progress: 'En progreso',
        ready: 'Listo',
        delivered: 'Entregado',
        cancelled: 'Cancelado'
    };
    return labels[status] ?? status;
}

function getTransitionOptions(status) {
    return (VALID_TRANSITIONS[status] ?? []).map((s) => ({ label: statusLabel(s), value: s }));
}

function handleError(err) {
    if (handleAuthError(err)) return;
    errorMessage.value = err.message ?? 'An unexpected error occurred.';
}

onMounted(async () => {
    try {
        const [ticketsData, clientsData] = await Promise.all([getTickets(), getClients()]);
        tickets.value = ticketsData;
        clients.value = clientsData;
    } catch (err) {
        if (handleAuthError(err)) return;
        loadError.value = err.message ?? 'Failed to load data.';
    }
});

function openNew() {
    ticket.value = {};
    submitted.value = false;
    errorMessage.value = '';
    ticketDialog.value = true;
}

function editTicket(t) {
    ticket.value = { ...t };
    submitted.value = false;
    errorMessage.value = '';
    ticketDialog.value = true;
}

function hideDialog() {
    ticketDialog.value = false;
    submitted.value = false;
    errorMessage.value = '';
}

async function saveTicket() {
    submitted.value = true;
    errorMessage.value = '';

    if (!ticket.value.title?.trim()) return;
    if (!ticket.value.id && !ticket.value.client_id) return;

    try {
        if (ticket.value.id) {
            const updated = await updateTicket(ticket.value.id, ticket.value.title.trim(), ticket.value.description);
            const idx = tickets.value.findIndex((t) => t.id === ticket.value.id);
            if (idx !== -1) tickets.value[idx] = updated;
            toast.add({ severity: 'success', summary: 'Actualizado', detail: 'Ticket actualizado correctamente.', life: 3000 });
        } else {
            const created = await createTicket(ticket.value.client_id, ticket.value.title.trim(), ticket.value.description);
            tickets.value.push(created);
            toast.add({ severity: 'success', summary: 'Creado', detail: 'Ticket creado correctamente.', life: 3000 });
        }
        ticketDialog.value = false;
        ticket.value = {};
    } catch (err) {
        handleError(err);
    }
}

function confirmDeleteTicket(t) {
    ticket.value = t;
    errorMessage.value = '';
    deleteTicketDialog.value = true;
}

async function doDeleteTicket() {
    try {
        await deleteTicket(ticket.value.id);
        tickets.value = tickets.value.filter((t) => t.id !== ticket.value.id);
        deleteTicketDialog.value = false;
        ticket.value = {};
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Ticket eliminado correctamente.', life: 3000 });
    } catch (err) {
        deleteTicketDialog.value = false;
        handleError(err);
    }
}

async function onStatusChange(t, newStatus) {
    try {
        const updated = await updateTicketStatus(t.id, newStatus);
        const idx = tickets.value.findIndex((tk) => tk.id === t.id);
        if (idx !== -1) tickets.value[idx] = updated;
        toast.add({ severity: 'success', summary: 'Estado actualizado', detail: `Ticket movido a ${statusLabel(newStatus)}.`, life: 3000 });

        if (newStatus === 'ready') {
            if (updated.whatsapp_notification_sent === true) {
                toast.add({ severity: 'success', summary: 'WhatsApp', detail: 'Notificación enviada al cliente por WhatsApp.', life: 3000 });
            } else if (updated.whatsapp_notification_error === 'client_has_no_phone') {
                toast.add({ severity: 'warn', summary: 'WhatsApp', detail: 'No se pudo notificar: el cliente no tiene número registrado.', life: 4000 });
            }
        }
    } catch (err) {
        if (handleAuthError(err)) return;
        if (newStatus === 'ready' && err.status >= 500) {
            toast.add({ severity: 'warn', summary: 'WhatsApp', detail: 'No se pudo enviar la notificación de WhatsApp, intente nuevamente.', life: 4000 });
            return;
        }
        toast.add({ severity: 'error', summary: 'Error', detail: err.message ?? 'Failed to update status.', life: 3000 });
    }
}
</script>

<template>
    <div>
        <div class="card">
            <Toolbar class="mb-6">
                <template #start>
                    <Button label="Nuevo Ticket" icon="pi pi-plus" severity="secondary" @click="openNew" />
                </template>
            </Toolbar>

            <small v-if="loadError" class="text-red-500 block mb-4">{{ loadError }}</small>

            <DataTable :value="filteredTickets" dataKey="id">
                <template #header>
                    <div class="flex items-center justify-between">
                        <h4 class="m-0">Tickets</h4>
                        <Select v-model="filterStatus" :options="filterStatusOptions" optionLabel="label" optionValue="value" />
                    </div>
                </template>

                <Column field="title" header="Título" sortable style="min-width: 16rem"></Column>
                <Column field="description" header="Descripción" style="min-width: 20rem; max-width: 20rem">
                    <template #body="slotProps">
                        <span v-tooltip.top="slotProps.data.description" class="block truncate">{{ slotProps.data.description }}</span>
                    </template>
                </Column>
                <Column header="Estado" style="min-width: 14rem">
                    <template #body="slotProps">
                        <span v-if="VALID_TRANSITIONS[slotProps.data.status].length === 0" class="text-surface-400">
                            {{ statusLabel(slotProps.data.status) }}
                        </span>
                        <Select
                            v-else
                            :modelValue="null"
                            :options="getTransitionOptions(slotProps.data.status)"
                            optionLabel="label"
                            optionValue="value"
                            :placeholder="statusLabel(slotProps.data.status)"
                            @change="(e) => onStatusChange(slotProps.data, e.value)"
                            fluid
                        />
                    </template>
                </Column>
                <Column field="created_at" header="Fecha de Creación" sortable style="min-width: 14rem">
                    <template #body="slotProps">
                        {{ formatDate(slotProps.data.created_at) }}
                    </template>
                </Column>
                <Column field="updated_at" header="Última Actualización" sortable style="min-width: 14rem">
                    <template #body="slotProps">
                        {{ formatDate(slotProps.data.updated_at) }}
                    </template>
                </Column>
                <Column :exportable="false" style="min-width: 8rem">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" outlined rounded class="mr-2" @click="editTicket(slotProps.data)" />
                        <Button icon="pi pi-trash" outlined rounded severity="danger" @click="confirmDeleteTicket(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>
        </div>

        <Toast />

        <Dialog v-model:visible="ticketDialog" :style="{ width: '450px' }" :header="ticket.id ? 'Editar Ticket' : 'Nuevo Ticket'" :modal="true">
            <div class="flex flex-col gap-6">
                <div v-if="!ticket.id">
                    <label for="ticket-client" class="block font-bold mb-3">Cliente</label>
                    <Select
                        id="ticket-client"
                        v-model="ticket.client_id"
                        :options="clients"
                        optionLabel="name"
                        optionValue="id"
                        placeholder="Seleccionar un cliente"
                        filter
                        :invalid="submitted && !ticket.client_id"
                        fluid
                    >
                        <template #option="slotProps">
                            <div class="flex flex-col">
                                <span>{{ slotProps.option.name }}</span>
                                <small class="text-surface-400">{{ tickets.filter(t => t.client_id === slotProps.option.id).length }} tickets</small>
                            </div>
                        </template>
                    </Select>
                    <small v-if="submitted && !ticket.client_id" class="text-red-500">El cliente es requerido.</small>
                </div>
                <div>
                    <label for="ticket-title" class="block font-bold mb-3">Título</label>
                    <InputText id="ticket-title" v-model.trim="ticket.title" autofocus :invalid="submitted && !ticket.title" fluid />
                    <small v-if="submitted && !ticket.title" class="text-red-500">El título es requerido.</small>
                </div>
                <div>
                    <label for="ticket-description" class="block font-bold mb-3">Descripción</label>
                    <Textarea id="ticket-description" v-model="ticket.description" rows="3" fluid />
                </div>
                <small v-if="errorMessage" class="text-red-500">{{ errorMessage }}</small>
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" text @click="hideDialog" />
                <Button label="Guardar" icon="pi pi-check" @click="saveTicket" />
            </template>
        </Dialog>

        <Dialog v-model:visible="deleteTicketDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle text-3xl!" />
                <span v-if="ticket">¿Estás seguro de que deseas eliminar <b>{{ ticket.title }}</b>?</span>
            </div>
            <template #footer>
                <Button label="No" icon="pi pi-times" text @click="deleteTicketDialog = false" />
                <Button label="Sí" icon="pi pi-check" severity="danger" @click="doDeleteTicket" />
            </template>
        </Dialog>
    </div>
</template>

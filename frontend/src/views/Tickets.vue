<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { handleAuthError } from '@/services/AuthService.js';
import { useTicketsStore } from '@/stores/tickets.js';
import { useClientsStore } from '@/stores/clients.js';
import { useInventoryStore } from '@/stores/inventory.js';
import { useDrawerNavigation } from '@/composables/useDrawerNavigation.js';
import EntityDrawer from '@/components/EntityDrawer.vue';
import PlaceholderCell from '@/components/PlaceholderCell.vue';
import { formatDate, ticketStatusLabel as statusLabel } from '@/utils/format.js';

const VALID_TRANSITIONS = {
    pending: ['in_progress', 'cancelled'],
    in_progress: ['ready', 'cancelled'],
    ready: ['delivered', 'cancelled'],
    delivered: [],
    cancelled: []
};

const toast = useToast();
const ticketsStore = useTicketsStore();
const clientsStore = useClientsStore();
const inventoryStore = useInventoryStore();

const deleteTicketDialog = ref(false);
const ticket = ref({});
const ticketToDelete = ref({});
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
    if (filterStatus.value === 'all') return ticketsStore.items;
    return ticketsStore.items.filter((t) => t.status === filterStatus.value);
});

const nav = useDrawerNavigation(filteredTickets);

watch(
    () => [nav.currentId, nav.visible],
    () => {
        ticket.value = nav.isNew ? {} : { ...ticketsStore.byId(nav.currentId) };
        submitted.value = false;
        errorMessage.value = '';
    }
);

function getTransitionOptions(status) {
    return (VALID_TRANSITIONS[status] ?? []).map((s) => ({ label: statusLabel(s), value: s }));
}

function handleError(err) {
    if (handleAuthError(err)) return;
    errorMessage.value = err.message ?? 'An unexpected error occurred.';
}

onMounted(async () => {
    try {
        await Promise.all([ticketsStore.load(), clientsStore.load()]);
    } catch (err) {
        if (handleAuthError(err)) return;
        loadError.value = err.message ?? 'Failed to load data.';
    }
});

// --- Parts used: exit movements recorded from the ticket drawer ---
// Purely visual: nothing links the ticket and the items beyond the note.

const CLOSED_STATUSES = ['delivered', 'cancelled'];
// No :max on the quantity field: InputNumber would silently clamp to it.
const MAX_QUANTITY = 5000;

const partsDialog = ref(false);
const partLines = ref([]);
const partsNote = ref('');
const partsSaving = ref(false);
const partsLoadError = ref('');

const currentTicketClosed = computed(() => CLOSED_STATUSES.includes(ticketsStore.byId(nav.currentId)?.status));

function newPartLine() {
    return { itemId: null, quantity: 1, error: '' };
}

async function openPartsDialog() {
    partLines.value = [newPartLine()];
    partsNote.value = `Ticket #${nav.currentId}`;
    partsLoadError.value = '';
    partsDialog.value = true;
    try {
        await inventoryStore.load();
    } catch (err) {
        if (handleAuthError(err)) return;
        partsLoadError.value = err.message ?? 'No se pudo cargar el inventario.';
    }
}

// An item already on another line can't be picked again.
function itemOptionsFor(line) {
    const takenIds = new Set(partLines.value.filter((other) => other !== line).map((other) => other.itemId));
    return inventoryStore.items.filter((item) => !takenIds.has(item.id));
}

function isPartLineValid(line) {
    return line.itemId !== null && Number.isInteger(line.quantity) && line.quantity >= 1 && line.quantity <= MAX_QUANTITY;
}

function partErrorMessageFor(err) {
    if (err.status === 404) return 'El artículo no existe o fue desactivado.';
    if (err.status === 422) return `Cantidad no válida: debe ser un número entero entre 1 y ${MAX_QUANTITY}.`;
    return err.message ?? 'Ocurrió un error inesperado.';
}

// One exit per line, one after another: there is no batch endpoint, so a
// failure leaves the earlier lines saved. Saved lines leave the popup and
// failed ones stay with their error.
async function savePartsUsed() {
    if (partLines.value.length === 0 || !partLines.value.every(isPartLineValid)) return;
    partsSaving.value = true;
    const note = partsNote.value.trim() || null;
    const total = partLines.value.length;
    const failedLines = [];
    for (const line of partLines.value) {
        try {
            await inventoryStore.addMovement(line.itemId, 'exit', line.quantity, note);
        } catch (err) {
            if (handleAuthError(err)) return;
            failedLines.push({ ...line, error: partErrorMessageFor(err) });
        }
    }
    partsSaving.value = false;
    partLines.value = failedLines;
    const saved = total - failedLines.length;
    if (failedLines.length === 0) {
        partsDialog.value = false;
        toast.add({ severity: 'success', summary: 'Repuestos registrados', detail: `${saved} ${saved === 1 ? 'salida registrada' : 'salidas registradas'} en el inventario.`, life: 3000 });
    } else {
        toast.add({ severity: 'warn', summary: 'Registro incompleto', detail: `Se registraron ${saved} de ${total}. Revisa los artículos que fallaron.`, life: 4000 });
    }
}

async function saveTicket() {
    submitted.value = true;
    errorMessage.value = '';

    if (!ticket.value.title?.trim()) return;
    if (!ticket.value.id && !ticket.value.client_id) return;

    try {
        if (ticket.value.id) {
            await ticketsStore.update(ticket.value.id, ticket.value.title.trim(), ticket.value.description);
            submitted.value = false;
            toast.add({ severity: 'success', summary: 'Actualizado', detail: 'Ticket actualizado correctamente.', life: 3000 });
        } else {
            await ticketsStore.create(ticket.value.client_id, ticket.value.title.trim(), ticket.value.description);
            toast.add({ severity: 'success', summary: 'Creado', detail: 'Ticket creado correctamente.', life: 3000 });
            nav.close();
        }
    } catch (err) {
        handleError(err);
    }
}

function confirmDeleteTicket(t) {
    ticketToDelete.value = t;
    errorMessage.value = '';
    deleteTicketDialog.value = true;
}

async function doDeleteTicket() {
    try {
        await ticketsStore.remove(ticketToDelete.value.id);
        deleteTicketDialog.value = false;
        ticketToDelete.value = {};
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Ticket eliminado correctamente.', life: 3000 });
    } catch (err) {
        deleteTicketDialog.value = false;
        handleError(err);
    }
}

async function onStatusChange(t, newStatus) {
    try {
        const updated = await ticketsStore.setStatus(t.id, newStatus);
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
                    <Button label="Nuevo Ticket" icon="pi pi-plus" severity="secondary" @click="nav.openNew()" />
                </template>
            </Toolbar>

            <small v-if="loadError" class="text-red-500 block mb-4">{{ loadError }}</small>

            <DataTable :ref="nav.bindTable" :value="filteredTickets" data-key="id">
                <template #header>
                    <div class="flex items-center justify-between">
                        <h4 class="m-0">Tickets</h4>
                        <Select v-model="filterStatus" :options="filterStatusOptions" option-label="label" option-value="value" />
                    </div>
                </template>

                <Column field="title" header="Título" sortable style="min-width: 16rem"></Column>
                <Column field="description" header="Descripción" style="min-width: 20rem; max-width: 20rem">
                    <template #body="slotProps">
                        <PlaceholderCell :value="slotProps.data.description" placeholder="Sin descripción" truncate />
                    </template>
                </Column>
                <Column header="Estado" style="min-width: 14rem">
                    <template #body="slotProps">
                        <span v-if="VALID_TRANSITIONS[slotProps.data.status].length === 0" class="text-surface-400">
                            {{ statusLabel(slotProps.data.status) }}
                        </span>
                        <Select
                            v-else
                            :model-value="null"
                            :options="getTransitionOptions(slotProps.data.status)"
                            option-label="label"
                            option-value="value"
                            :placeholder="statusLabel(slotProps.data.status)"
                            fluid
                            @change="(e) => onStatusChange(slotProps.data, e.value)"
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
                        <Button icon="pi pi-pencil" outlined rounded class="mr-2" @click="nav.open(slotProps.data.id)" />
                        <Button icon="pi pi-trash" outlined rounded severity="danger" @click="confirmDeleteTicket(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>
        </div>

        <EntityDrawer :nav="nav" :header="nav.isNew ? 'Nuevo Ticket' : 'Editar Ticket'">
            <div class="flex flex-col gap-6">
                <div v-if="nav.isNew">
                    <label for="ticket-client" class="block font-bold mb-3">Cliente</label>
                    <Select id="ticket-client" v-model="ticket.client_id" :options="clientsStore.items" option-label="name" option-value="id" placeholder="Seleccionar un cliente" filter :invalid="submitted && !ticket.client_id" fluid>
                        <template #option="slotProps">
                            <div class="flex flex-col">
                                <span>{{ slotProps.option.name }}</span>
                                <small class="text-surface-400">{{ ticketsStore.items.filter((t) => t.client_id === slotProps.option.id).length }} tickets</small>
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
                <div v-if="!nav.isNew">
                    <Button label="Registrar repuestos usados" icon="pi pi-box" severity="secondary" outlined fluid :disabled="currentTicketClosed" @click="openPartsDialog" />
                    <small v-if="currentTicketClosed" class="text-surface-500 block mt-2">No disponible para tickets entregados o cancelados.</small>
                </div>
                <small v-if="errorMessage" class="text-red-500">{{ errorMessage }}</small>
            </div>
            <template #footer>
                <div class="flex justify-end gap-2">
                    <Button label="Cancelar" icon="pi pi-times" text @click="nav.close()" />
                    <Button label="Guardar" icon="pi pi-check" @click="saveTicket" />
                </div>
            </template>
        </EntityDrawer>

        <Dialog v-model:visible="partsDialog" :style="{ width: '560px' }" header="Registrar repuestos usados" :modal="true" :closable="!partsSaving">
            <div class="flex flex-col gap-4">
                <small v-if="partsLoadError" class="text-red-500">{{ partsLoadError }}</small>
                <div v-for="(line, index) in partLines" :key="index" class="flex flex-col gap-1">
                    <div class="flex items-center gap-2">
                        <Select
                            v-model="line.itemId"
                            :options="itemOptionsFor(line)"
                            option-label="name"
                            option-value="id"
                            placeholder="Seleccionar un artículo"
                            filter
                            :disabled="partsSaving"
                            :invalid="!!line.error"
                            class="flex-1 min-w-0"
                        >
                            <template #option="slotProps">
                                <div class="flex items-center justify-between w-full gap-4">
                                    <span>{{ slotProps.option.name }}</span>
                                    <small class="text-surface-400 whitespace-nowrap">Stock: {{ slotProps.option.stock }}</small>
                                </div>
                            </template>
                        </Select>
                        <InputNumber v-model="line.quantity" :min="1" @input="(event) => (line.quantity = event.value)" :use-grouping="false" :invalid="line.quantity > MAX_QUANTITY" :disabled="partsSaving" :aria-label="`Cantidad de la línea ${index + 1}`" input-class="w-20 text-center" />
                        <Button v-tooltip.top="'Quitar'" icon="pi pi-times" text rounded severity="secondary" :disabled="partsSaving || partLines.length === 1" @click="partLines.splice(index, 1)" />
                    </div>
                    <small v-if="line.quantity > MAX_QUANTITY" class="text-red-500">Máximo {{ MAX_QUANTITY }} por artículo.</small>
                    <small v-if="line.error" class="text-red-500">{{ line.error }}</small>
                </div>
                <div>
                    <Button label="Agregar artículo" icon="pi pi-plus" text :disabled="partsSaving" @click="partLines.push(newPartLine())" />
                </div>
                <div>
                    <label for="parts-note" class="block font-bold mb-3">Nota</label>
                    <InputText id="parts-note" v-model="partsNote" :maxlength="500" :disabled="partsSaving" fluid />
                    <small class="text-surface-500 block mt-2">Se guarda en cada salida del historial del artículo.</small>
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" text :disabled="partsSaving" @click="partsDialog = false" />
                <Button label="Registrar salidas" icon="pi pi-check" :loading="partsSaving" :disabled="partLines.length === 0 || !partLines.every(isPartLineValid)" @click="savePartsUsed" />
            </template>
        </Dialog>

        <Dialog v-model:visible="deleteTicketDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle text-3xl!" />
                <span v-if="ticketToDelete"
                    >¿Estás seguro de que deseas eliminar <b>{{ ticketToDelete.title }}</b
                    >?</span
                >
            </div>
            <template #footer>
                <Button label="No" icon="pi pi-times" text @click="deleteTicketDialog = false" />
                <Button label="Sí" icon="pi pi-check" severity="danger" @click="doDeleteTicket" />
            </template>
        </Dialog>
    </div>
</template>

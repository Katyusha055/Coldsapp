<script setup>
import { ref, computed, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { handleAuthError } from '@/services/AuthService.js';
import { getStatus, getQR, setNotificationsEnabled } from '@/services/WhatsappService.js';
import { usePendingsStore } from '@/stores/pendings.js';
import { useClientsStore } from '@/stores/clients.js';
import { useWhatsappEvents } from '@/composables/useWhatsappEvents.js';
import PlaceholderCell from '@/components/PlaceholderCell.vue';
import { formatDate, formatPhone, localPhoneFromJid } from '@/utils/format.js';

const toast = useToast();
const pendingsStore = usePendingsStore();
const clientsStore = useClientsStore();

const status = ref('');
const loadError = ref('');
const errorMessage = ref('');

const notificationsEnabled = ref(true);

const qr = ref('');
const qrDialog = ref(false);
const qrLoading = ref(false);

const deleteDialog = ref(false);
const pending = ref({});

const convertDialog = ref(false);
const convertForm = ref({});
const convertSubmitted = ref(false);

const isConnected = computed(() => status.value === 'open');
const isPhoneValid = computed(() => {
    const phone = convertForm.value.phone?.trim();
    return !phone || /^\d{10}$/.test(phone);
});

function handleError(err) {
    if (handleAuthError(err)) return;
    errorMessage.value = err.message ?? 'An unexpected error occurred.';
}

onMounted(async () => {
    try {
        const [statusData] = await Promise.all([getStatus(), pendingsStore.load(true)]);
        status.value = statusData.status;
        notificationsEnabled.value = statusData.notifications_enabled ?? true;
    } catch (err) {
        if (handleAuthError(err)) return;
        loadError.value = err.message ?? 'Failed to load WhatsApp data.';
    }
});

useWhatsappEvents({
    onConnectionUpdate(newStatus) {
        status.value = newStatus;
        if (newStatus === 'open') {
            qrDialog.value = false;
            qr.value = null;
        }
    },
    onQrUpdated() {
        if (qrDialog.value) generateQR();
    }
});

async function onNotificationsToggle() {
    try {
        await setNotificationsEnabled(notificationsEnabled.value);
        toast.add({
            severity: 'success',
            summary: 'Guardado',
            detail: notificationsEnabled.value ? 'Notificaciones automáticas activadas.' : 'Notificaciones automáticas desactivadas.',
            life: 3000
        });
    } catch (err) {
        notificationsEnabled.value = !notificationsEnabled.value;
        if (handleAuthError(err)) return;
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo actualizar la preferencia.', life: 3000 });
    }
}

async function generateQR() {
    errorMessage.value = '';
    qrLoading.value = true;
    try {
        const data = await getQR();
        qr.value = data.qr;
        qrDialog.value = true;
    } catch (err) {
        handleError(err);
    } finally {
        qrLoading.value = false;
    }
}

async function discardPending(row) {
    try {
        await pendingsStore.resolve(row.id, 'discarded');
        toast.add({ severity: 'success', summary: 'Descartado', detail: 'Contacto descartado correctamente.', life: 3000 });
    } catch (err) {
        handleError(err);
    }
}

function confirmDeletePending(row) {
    pending.value = row;
    errorMessage.value = '';
    deleteDialog.value = true;
}

async function doDeletePending() {
    try {
        await pendingsStore.remove(pending.value.id);
        deleteDialog.value = false;
        pending.value = {};
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Contacto eliminado correctamente.', life: 3000 });
    } catch (err) {
        deleteDialog.value = false;
        handleError(err);
    }
}

function notifyPhoneNotFilled(remoteJid) {
    const detail = remoteJid?.endsWith('@lid')
        ? 'WhatsApp oculta el número de este contacto. Ingresa el teléfono manualmente.'
        : 'El número no es de Ecuador. Ingresa el teléfono manualmente.';
    toast.add({ severity: 'info', summary: 'Teléfono no completado', detail, life: 5000 });
}

function openConvertDialog(row) {
    pending.value = row;
    const phone = localPhoneFromJid(row.remote_jid);
    if (!phone) notifyPhoneNotFilled(row.remote_jid);
    convertForm.value = { name: row.name ?? '', phone, description: '' };
    convertSubmitted.value = false;
    errorMessage.value = '';
    convertDialog.value = true;
}

function hideConvertDialog() {
    convertDialog.value = false;
    convertSubmitted.value = false;
    errorMessage.value = '';
}

async function convertToClient() {
    convertSubmitted.value = true;
    errorMessage.value = '';

    if (!convertForm.value.name?.trim()) return;
    if (!isPhoneValid.value) return;

    try {
        const payload = { 
            name: convertForm.value.name.trim(), 
            whatsapp_id: pending.value.remote_jid
        };
        if (convertForm.value.phone?.trim()) payload.phone = convertForm.value.phone.trim();
        if (convertForm.value.description) payload.description = convertForm.value.description;
        await clientsStore.create(payload);
    } catch (err) {
        handleError(err);
        return;
    }

    try {
        await pendingsStore.resolve(pending.value.id, 'converted');
        convertDialog.value = false;
        pending.value = {};
        toast.add({ severity: 'success', summary: 'Convertido', detail: 'Contacto convertido a cliente correctamente.', life: 3000 });
    } catch (err) {
        handleError(err);
    }
}
</script>

<template>
    <div>
        <div class="card mb-6">
            <div class="flex items-center justify-between flex-wrap gap-4">
                <div class="flex items-center gap-3">
                    <h4 class="m-0">WhatsApp</h4>
                    <Badge :value="status || 'desconocido'" :severity="isConnected ? 'success' : 'danger'" />
                </div>
                <div class="flex items-center gap-4">
                    <div class="flex items-center gap-2">
                        <label for="notif-toggle" class="text-sm font-medium">Notificaciones automáticas</label>
                        <ToggleSwitch inputId="notif-toggle" v-model="notificationsEnabled" @change="onNotificationsToggle" />
                    </div>
                    <Button label="Generar QR" icon="pi pi-qrcode" :disabled="isConnected" :loading="qrLoading" @click="generateQR" />
                </div>
            </div>
            <small v-if="!isConnected" class="text-yellow-500 block mt-3">Se ha perdido la conexión, presione para generar el QR</small>
            <small v-if="loadError" class="text-red-500 block mt-3">{{ loadError }}</small>
            <small v-if="errorMessage && !convertDialog" class="text-red-500 block mt-3">{{ errorMessage }}</small>
        </div>

        <div class="card">
            <DataTable :value="pendingsStore.items" dataKey="id">
                <template #header>
                    <div class="flex items-center justify-between">
                        <h4 class="m-0">Posibles Clientes Nuevos</h4>
                    </div>
                </template>

                <Column field="name" header="Nombre" sortable style="min-width: 14rem">
                    <template #body="slotProps">
                        <PlaceholderCell :value="slotProps.data.name" placeholder="Sin Nombre" />
                    </template>
                </Column>
                <Column field="last_message" header="Último Mensaje" style="min-width: 20rem; max-width: 20rem">
                    <template #body="slotProps">
                        <PlaceholderCell :value="slotProps.data.last_message" placeholder="Mensaje sin texto" truncate />
                    </template>
                </Column>
                <Column header="Fecha" style="min-width: 14rem">
                    <template #body="slotProps">
                        {{ formatDate(slotProps.data.last_message_at ?? slotProps.data.created_at) }}
                    </template>
                </Column>
                <Column :exportable="false" style="min-width: 24rem">
                    <template #body="slotProps">
                        <Button label="Convertir a cliente" icon="pi pi-user-plus" outlined class="mr-2 mb-2" @click="openConvertDialog(slotProps.data)" />
                        <Button label="Descartar" icon="pi pi-times" outlined severity="secondary" class="mr-2 mb-2" @click="discardPending(slotProps.data)" />
                        <Button label="Eliminar" icon="pi pi-trash" outlined severity="danger" class="mb-2" @click="confirmDeletePending(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>
        </div>


        <!-- QR Dialog -->
        <Dialog v-model:visible="qrDialog" :style="{ width: '350px' }" header="Código QR" :modal="true">
            <div class="flex flex-col items-center gap-4">
                <img v-if="qr" :src="qr" alt="QR" style="max-width: 100%" />
            </div>
        </Dialog>

        <!-- Convert to Client Dialog -->
        <Dialog v-model:visible="convertDialog" :style="{ width: '450px' }" header="Convertir a Cliente" :modal="true">
            <div class="flex flex-col gap-6">
                <div>
                    <label for="convert-name" class="block font-bold mb-3">Nombre</label>
                    <InputText id="convert-name" v-model.trim="convertForm.name" autofocus :invalid="convertSubmitted && !convertForm.name" fluid />
                    <small v-if="convertSubmitted && !convertForm.name" class="text-red-500">El nombre es requerido.</small>
                </div>
                <div>
                    <label for="convert-phone" class="block font-bold mb-3">Teléfono</label>
                    <InputText id="convert-phone" v-model="convertForm.phone" :invalid="convertSubmitted && !isPhoneValid" fluid />
                    <small v-if="convertSubmitted && !isPhoneValid" class="text-red-500">El teléfono debe tener exactamente 10 dígitos.</small>
                </div>
                <div>
                    <label for="convert-description" class="block font-bold mb-3">Descripción</label>
                    <Textarea id="convert-description" v-model="convertForm.description" rows="3" fluid />
                </div>
                <small v-if="errorMessage" class="text-red-500">{{ errorMessage }}</small>
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" text @click="hideConvertDialog" />
                <Button label="Guardar" icon="pi pi-check" @click="convertToClient" />
            </template>
        </Dialog>

        <!-- Delete Confirmation Dialog -->
        <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle text-3xl!" />
                <span v-if="pending">¿Estás seguro de que deseas eliminar el contacto <b>{{ pending.name || formatPhone(pending.remote_jid) }}</b>?</span>
            </div>
            <template #footer>
                <Button label="No" icon="pi pi-times" text @click="deleteDialog = false" />
                <Button label="Sí" icon="pi pi-check" severity="danger" @click="doDeletePending" />
            </template>
        </Dialog>
    </div>
</template>

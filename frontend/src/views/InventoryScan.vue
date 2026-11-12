<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { handleAuthError } from '@/services/AuthService.js';
import { getItemByCode } from '@/services/BarcodeService.js';
import { useInventoryStore } from '@/stores/inventory.js';
import { useBarcodeScanner } from '@/composables/useBarcodeScanner.js';
import ScannedItemDrawer from '@/components/ScannedItemDrawer.vue';

// Same limits as the backend: item name, quantities, and raw code input.
const MAX_NAME_LENGTH = 200;
const MAX_QUANTITY = 5000;
const MAX_CODE_INPUT_LENGTH = 64;

const router = useRouter();
const toast = useToast();
const store = useInventoryStore();

const video = ref(null);
const scanner = useBarcodeScanner(video);
const chosenDeviceId = ref(null);

// A soft hint only: a laptop with a movable autofocus webcam also works.
const hasTouchScreen = window.matchMedia?.('(pointer: coarse)').matches ?? false;

const loadError = ref('');
const lookupBusy = ref(false);
const lookupError = ref('');
const typedCode = ref('');

// What the view shows after a lookup: the found item's drawer, or the
// options for a code no item has. Neither means the camera is scanning.
const foundItemId = ref(null);
const unknownCode = ref(null);
const unknownMode = ref(null); // null (the three options), 'link' or 'create'

const linkItemId = ref(null);
const newItem = ref({ name: '', quantity: 0, lowStockThreshold: null });
const submitted = ref(false);
const saving = ref(false);

const itemOptions = computed(() => [...store.items].sort((a, b) => a.name.localeCompare(b.name)));

function isQuantityInRange(value, min) {
    return Number.isInteger(value) && value >= min && value <= MAX_QUANTITY;
}

function isOverCap(value) {
    return Number.isInteger(value) && value > MAX_QUANTITY;
}

function errorMessageFor(err) {
    if (err.status === 404) return 'El artículo no existe o fue desactivado.';
    if (err.status === 409) return 'Ese código ya está vinculado a otro artículo.';
    if (err.status === 422) return 'Código no válido: debe ser un EAN-13 o UPC-A con su dígito verificador correcto.';
    return err.message ?? 'Ocurrió un error inesperado.';
}

onMounted(async () => {
    scanner.start();
    try {
        await store.load();
    } catch (err) {
        if (handleAuthError(err)) return;
        loadError.value = 'No se pudo cargar el inventario.';
    }
});

function resumeScanning() {
    foundItemId.value = null;
    unknownCode.value = null;
    unknownMode.value = null;
    scanner.start(chosenDeviceId.value);
}

function chooseCamera(deviceId) {
    chosenDeviceId.value = deviceId;
    scanner.start(deviceId);
}

watch(
    () => scanner.result.value,
    (text) => {
        if (text) lookup(text);
    }
);

function submitTypedCode() {
    const code = typedCode.value.trim();
    if (!code || lookupBusy.value) return;
    scanner.stop();
    typedCode.value = '';
    lookup(code);
}

// The code goes to the server as read or typed: it normalizes and validates
// it, so a typed 12-digit UPC-A finds the same item as its 13-digit scan.
async function lookup(code) {
    lookupBusy.value = true;
    lookupError.value = '';
    foundItemId.value = null;
    unknownCode.value = null;
    try {
        const item = await getItemByCode(code);
        // The store is loaded once; an item created on another device since
        // then is added here so the drawer can read it.
        store.upsertOne(item);
        foundItemId.value = item.id;
    } catch (err) {
        if (handleAuthError(err)) return;
        if (err.status === 404) {
            unknownCode.value = code;
            unknownMode.value = null;
        } else {
            lookupError.value = errorMessageFor(err);
            scanner.start(chosenDeviceId.value);
        }
    } finally {
        lookupBusy.value = false;
    }
}

function startLink() {
    linkItemId.value = null;
    unknownMode.value = 'link';
}

function startCreate() {
    newItem.value = { name: '', quantity: 0, lowStockThreshold: null };
    submitted.value = false;
    unknownMode.value = 'create';
}

// "Vincular" and "Crear" are disabled while saving: a double tap on "Crear"
// would create the item and then get a 409 for the same code.
async function save(action) {
    if (saving.value) return;
    saving.value = true;
    try {
        const item = await action();
        unknownCode.value = null;
        unknownMode.value = null;
        foundItemId.value = item.id;
    } catch (err) {
        if (!handleAuthError(err)) toast.add({ severity: 'error', summary: 'Error', detail: errorMessageFor(err), life: 4000 });
    } finally {
        saving.value = false;
    }
}

async function linkToItem() {
    if (linkItemId.value === null) return;
    const itemId = linkItemId.value;
    const code = unknownCode.value;
    await save(async () => {
        const item = await store.linkCode(itemId, code);
        toast.add({ severity: 'success', summary: 'Código vinculado', detail: `${code} quedó vinculado a ${item.name}.`, life: 3000 });
        return item;
    });
}

async function createWithCode() {
    submitted.value = true;
    const name = newItem.value.name.trim();
    const { quantity, lowStockThreshold } = newItem.value;
    if (!name || !isQuantityInRange(quantity, 0) || isOverCap(lowStockThreshold)) return;
    const code = unknownCode.value;
    await save(async () => {
        const item = await store.create(name, quantity, lowStockThreshold ?? null, code);
        toast.add({ severity: 'success', summary: 'Creado', detail: 'Artículo creado con su código.', life: 3000 });
        return item;
    });
}
</script>

<template>
    <div class="max-w-xl mx-auto">
        <div class="card flex flex-col gap-4">
            <div class="flex items-center justify-between gap-2">
                <h4 class="m-0">Escanear código</h4>
                <Button label="Inventario" icon="pi pi-arrow-left" text @click="router.push({ name: 'inventory' })" />
            </div>

            <small v-if="loadError" class="text-red-500">{{ loadError }}</small>

            <!-- Kept in the DOM (v-show) so the scanner always has its element. -->
            <div v-show="scanner.starting.value || scanner.scanning.value" class="relative">
                <video ref="video" class="w-full rounded-lg bg-black object-cover" style="max-height: 55vh" playsinline muted></video>
            </div>

            <Message v-if="scanner.error.value" severity="warn">{{ scanner.error.value }}</Message>

            <template v-if="scanner.scanning.value">
                <span>Apunta la cámara al código de barras.</span>
                <small class="text-surface-500">Si no enfoca, aleja un poco el celular.</small>
            </template>
            <span v-else-if="scanner.starting.value" class="text-surface-500">Abriendo cámara…</span>
            <Button v-else-if="scanner.paused.value" label="Reanudar" icon="pi pi-play" size="large" @click="resumeScanning" />

            <div v-if="scanner.cameras.value.length > 1 || scanner.torchSupported.value" class="flex flex-wrap items-center gap-2">
                <Select
                    v-if="scanner.cameras.value.length > 1"
                    :model-value="scanner.activeDeviceId.value"
                    :options="scanner.cameras.value"
                    option-label="label"
                    option-value="deviceId"
                    placeholder="Cámara"
                    empty-message="No hay cámaras"
                    class="flex-1"
                    @update:model-value="chooseCamera"
                />
                <Button v-if="scanner.torchSupported.value" :label="scanner.torchOn.value ? 'Apagar linterna' : 'Linterna'" icon="pi pi-sun" :outlined="!scanner.torchOn.value" severity="secondary" @click="scanner.toggleTorch()" />
            </div>

            <small v-if="!hasTouchScreen && !scanner.error.value" class="text-surface-500">El escaneo funciona mejor desde el celular.</small>

            <div>
                <label for="typed-code" class="block font-bold mb-2">O escribe el código</label>
                <div class="flex gap-2">
                    <InputText id="typed-code" v-model="typedCode" inputmode="numeric" autocomplete="off" :maxlength="MAX_CODE_INPUT_LENGTH" placeholder="12 o 13 dígitos" class="flex-1" @keyup.enter="submitTypedCode" />
                    <Button label="Buscar" icon="pi pi-search" :disabled="!typedCode.trim() || lookupBusy" @click="submitTypedCode" />
                </div>
            </div>

            <span v-if="lookupBusy" class="text-surface-500">Buscando…</span>
            <Message v-if="lookupError" severity="error">{{ lookupError }}</Message>
        </div>

        <div v-if="unknownCode" class="card flex flex-col gap-4">
            <span
                >El código <b class="font-mono">{{ unknownCode }}</b> no está vinculado a ningún artículo.</span
            >

            <div v-if="unknownMode === null" class="flex flex-col gap-2">
                <Button label="Vincular a un artículo" icon="pi pi-link" size="large" @click="startLink" />
                <Button label="Crear artículo" icon="pi pi-plus" size="large" severity="secondary" @click="startCreate" />
                <Button label="Ignorar" icon="pi pi-times" size="large" text @click="resumeScanning" />
            </div>

            <div v-else-if="unknownMode === 'link'" class="flex flex-col gap-3">
                <label for="link-item" class="font-bold">Artículo</label>
                <Select
                    v-model="linkItemId"
                    input-id="link-item"
                    :options="itemOptions"
                    option-label="name"
                    option-value="id"
                    filter
                    placeholder="Elige un artículo"
                    empty-message="Aún no hay artículos"
                    empty-filter-message="Ningún artículo coincide"
                    fluid
                />
                <div class="flex gap-2">
                    <Button label="Volver" icon="pi pi-arrow-left" text :disabled="saving" @click="unknownMode = null" />
                    <Button label="Vincular" icon="pi pi-check" size="large" class="flex-1" :disabled="linkItemId === null || saving" @click="linkToItem" />
                </div>
            </div>

            <div v-else-if="unknownMode === 'create'" class="flex flex-col gap-4">
                <div>
                    <label for="scan-new-name" class="block font-bold mb-2">Nombre</label>
                    <InputText id="scan-new-name" v-model="newItem.name" :maxlength="MAX_NAME_LENGTH" :invalid="submitted && !newItem.name.trim()" fluid />
                    <small v-if="submitted && !newItem.name.trim()" class="text-red-500">El nombre es requerido.</small>
                </div>
                <div>
                    <label for="scan-new-quantity" class="block font-bold mb-2">Cantidad inicial</label>
                    <InputNumber
                        v-model="newItem.quantity"
                        input-id="scan-new-quantity"
                        :min="0"
                        :use-grouping="false"
                        :invalid="isOverCap(newItem.quantity) || (submitted && !Number.isInteger(newItem.quantity))"
                        fluid
                        @input="(event) => (newItem.quantity = event.value)"
                    />
                    <small v-if="isOverCap(newItem.quantity)" class="text-red-500">Máximo {{ MAX_QUANTITY }}.</small>
                    <small v-else-if="submitted && !Number.isInteger(newItem.quantity)" class="text-red-500">La cantidad es requerida.</small>
                </div>
                <div>
                    <label for="scan-new-threshold" class="block font-bold mb-2">Umbral de stock bajo</label>
                    <InputNumber
                        v-model="newItem.lowStockThreshold"
                        input-id="scan-new-threshold"
                        :min="0"
                        :use-grouping="false"
                        :invalid="isOverCap(newItem.lowStockThreshold)"
                        placeholder="Sin alerta"
                        fluid
                        @input="(event) => (newItem.lowStockThreshold = event.value)"
                    />
                    <small v-if="isOverCap(newItem.lowStockThreshold)" class="text-red-500 block mt-1">Máximo {{ MAX_QUANTITY }}.</small>
                    <small class="text-surface-500 block mt-1">Opcional. Si lo dejas vacío, no tendrá alerta de stock bajo.</small>
                </div>
                <div>
                    <label for="scan-new-code" class="block font-bold mb-2">Código</label>
                    <InputText id="scan-new-code" :model-value="unknownCode" readonly class="font-mono" fluid />
                </div>
                <div class="flex gap-2">
                    <Button label="Volver" icon="pi pi-arrow-left" text :disabled="saving" @click="unknownMode = null" />
                    <Button label="Crear" icon="pi pi-check" size="large" class="flex-1" :disabled="saving" @click="createWithCode" />
                </div>
            </div>
        </div>

        <ScannedItemDrawer :item-id="foundItemId" @close="resumeScanning" />
    </div>
</template>

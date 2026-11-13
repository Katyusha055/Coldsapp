<script setup>
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { handleAuthError } from '@/services/AuthService.js';
import { useInventoryStore, isNegativeStock, isLowStock } from '@/stores/inventory.js';
import ItemCodeList from '@/components/ItemCodeList.vue';

// A phone drawer for the item a scan found: only what you do with a part in
// hand (see and change its stock, fix its codes). Everything else is on the
// inventory page, one tap away through "Ver en inventario". It shows one item,
// so it isn't built on EntityDrawer (no previous/next).

// Same cap as the backend and the inventory page. No :max on the number
// fields: InputNumber would silently clamp a typed 6000 to 5000.
const MAX_QUANTITY = 5000;

const props = defineProps({
    itemId: { type: Number, default: null }
});
const emit = defineEmits(['close']);

const store = useInventoryStore();
const router = useRouter();
const toast = useToast();

// Read from the store, so every change made here or elsewhere shows up.
const item = computed(() => (props.itemId === null ? null : store.byId(props.itemId)));

const step = ref(1);
const counted = ref(null);
const busy = ref(false);

watch(
    () => props.itemId,
    () => {
        step.value = 1;
        counted.value = null;
    }
);

function isQuantityInRange(value, min) {
    return Number.isInteger(value) && value >= min && value <= MAX_QUANTITY;
}

function isOverCap(value) {
    return Number.isInteger(value) && value > MAX_QUANTITY;
}

function stockSeverity(target) {
    if (isNegativeStock(target)) return 'danger';
    if (isLowStock(target)) return 'warn';
    return null;
}

function errorMessageFor(err) {
    if (err.alreadyUnlinked) return 'Ese código ya se había quitado, quizás desde otro dispositivo. La lista ya está actualizada.';
    if (err.status === 404) return 'El artículo no existe o fue desactivado.';
    if (err.status === 422) return 'Datos no válidos. Revisa los campos e intenta de nuevo.';
    return err.message ?? 'Ocurrió un error inesperado.';
}

// One request at a time: every button is disabled while one is in flight.
async function run(action) {
    if (busy.value) return;
    busy.value = true;
    try {
        await action();
    } catch (err) {
        if (!handleAuthError(err)) toast.add({ severity: 'error', summary: 'Error', detail: errorMessageFor(err), life: 3000 });
    } finally {
        busy.value = false;
    }
}

async function applyMovement(type) {
    if (!item.value || !isQuantityInRange(step.value, 1)) return;
    const { id } = item.value;
    const quantity = step.value;
    await run(() => store.addMovement(id, type, quantity));
    // Back to 1 even on failure, like the inventory page's row actions.
    step.value = 1;
}

async function saveCount() {
    if (!item.value || !isQuantityInRange(counted.value, 0)) return;
    const { id, name } = item.value;
    const quantity = counted.value;
    await run(async () => {
        await store.count(id, quantity);
        counted.value = null;
        toast.add({ severity: 'success', summary: 'Conteo guardado', detail: `${name}: stock ajustado a ${quantity}.`, life: 3000 });
    });
}

// code is the normalized form from item.codes.
async function removeCode(code) {
    if (!item.value) return;
    const { id, name } = item.value;
    await run(async () => {
        await store.unlinkCode(id, code);
        toast.add({ severity: 'success', summary: 'Código quitado', detail: `${code} ya no está vinculado a ${name}.`, life: 3000 });
    });
}

function seeInInventory() {
    router.push({ name: 'inventory', query: { item: props.itemId } });
}
</script>

<template>
    <Drawer :visible="itemId !== null" position="bottom" :style="{ height: 'auto', maxHeight: '90vh' }" @update:visible="(value) => !value && emit('close')">
        <template #header>
            <span class="font-semibold text-xl">{{ item ? item.name : 'Artículo' }}</span>
        </template>

        <div v-if="!item" class="italic text-surface-500">El artículo ya no está en el inventario.</div>

        <div v-else class="flex flex-col gap-6">
            <div class="flex items-center justify-between gap-4">
                <span class="font-bold">Stock actual</span>
                <Tag v-if="stockSeverity(item)" :severity="stockSeverity(item)"
                    ><span class="text-2xl font-semibold px-2">{{ item.stock }}</span></Tag
                >
                <span v-else class="text-2xl font-semibold">{{ item.stock }}</span>
            </div>

            <div>
                <span class="block font-bold mb-3">Restar o sumar</span>
                <div class="flex items-center gap-2">
                    <Button icon="pi pi-minus" size="large" outlined severity="secondary" aria-label="Restar" :disabled="!isQuantityInRange(step, 1) || busy" @click="applyMovement('exit')" />
                    <!-- @input keeps the value current while typing; InputNumber only commits it on blur. -->
                    <InputNumber v-model="step" :min="1" :use-grouping="false" :invalid="!isQuantityInRange(step, 1)" aria-label="Cantidad" input-class="text-center text-lg" class="flex-1" fluid @input="(event) => (step = event.value)" />
                    <Button icon="pi pi-plus" size="large" outlined severity="secondary" aria-label="Sumar" :disabled="!isQuantityInRange(step, 1) || busy" @click="applyMovement('entry')" />
                </div>
                <small v-if="isOverCap(step)" class="text-red-500 block mt-2">Máximo {{ MAX_QUANTITY }}.</small>
            </div>

            <div>
                <label for="scanned-counted" class="block font-bold mb-3">Conteo rápido</label>
                <div class="flex items-center gap-2">
                    <InputNumber v-model="counted" input-id="scanned-counted" :min="0" :use-grouping="false" :invalid="isOverCap(counted)" placeholder="Cantidad contada" input-class="text-lg" class="flex-1" fluid @input="(event) => (counted = event.value)" />
                    <Button label="Contar" icon="pi pi-calculator" size="large" :disabled="!isQuantityInRange(counted, 0) || busy" @click="saveCount" />
                </div>
                <small v-if="isOverCap(counted)" class="text-red-500 block mt-2">Máximo {{ MAX_QUANTITY }} por conteo.</small>
            </div>

            <div>
                <span class="block font-bold mb-3">Códigos</span>
                <ItemCodeList :codes="item.codes" :busy="busy" large @remove="removeCode" />
            </div>
        </div>

        <template #footer>
            <div class="flex flex-col sm:flex-row gap-2">
                <Button label="Ver en inventario" icon="pi pi-external-link" size="large" outlined class="flex-1" :disabled="!item" @click="seeInInventory" />
                <Button label="Escanear otro" icon="pi pi-camera" size="large" class="flex-1" @click="emit('close')" />
            </div>
        </template>
    </Drawer>
</template>

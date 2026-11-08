<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { handleAuthError } from '@/services/AuthService.js';
import { useInventoryStore, isNegativeStock, isLowStock, hasStockAlert } from '@/stores/inventory.js';
import { useDrawerNavigation } from '@/composables/useDrawerNavigation.js';
import EntityDrawer from '@/components/EntityDrawer.vue';
import { formatDate, movementTypeLabel } from '@/utils/format.js';

// Same cap the backend applies to every quantity, count and threshold.
// The number fields have no :max on purpose: InputNumber silently clamps to it
// on blur and Enter, so a typed 6000 would be saved as 5000. A value over the
// cap is shown as an error and blocks saving instead.
const MAX_QUANTITY = 5000;
// Same limit as the backend's item name.
const MAX_NAME_LENGTH = 200;

function isQuantityInRange(value, min) {
    return Number.isInteger(value) && value >= min && value <= MAX_QUANTITY;
}

function isOverCap(value) {
    return Number.isInteger(value) && value > MAX_QUANTITY;
}

const toast = useToast();
const route = useRoute();
const store = useInventoryStore();

const loadError = ref('');

const searchQuery = ref('');
const tableFirst = ref(0);

watch(searchQuery, () => {
    tableFirst.value = 0;
});

// Always in name order: a newly created item is appended to the store, so
// the backend's order alone would show it at the end until a reload.
const filteredItems = computed(() => {
    const query = searchQuery.value.trim().toLowerCase();
    const matches = query ? store.items.filter((item) => item.name.toLowerCase().includes(query)) : store.items;
    return [...matches].sort((a, b) => a.name.localeCompare(b.name) || a.id - b.id);
});

// "Mostrar alertas" sorts rather than filters: alerts first (negative, then
// low, then by name), and the rest below in name order. The
// dashboard widget links here with ?alerts=1 to open it already on.
const showAlerts = ref(false);

watch(
    () => route.query.alerts,
    (alerts) => {
        showAlerts.value = alerts === '1';
    },
    { immediate: true }
);

function alertRank(item) {
    if (isNegativeStock(item)) return 0;
    if (isLowStock(item)) return 1;
    return 2;
}

const displayedItems = computed(() => {
    if (!showAlerts.value) return filteredItems.value;
    return [...filteredItems.value].sort((a, b) => alertRank(a) - alertRank(b) || a.name.localeCompare(b.name));
});

// A column sort set from a header overrides the order of :value, so the two
// orders take turns: turning alerts on clears the column sort, and sorting a
// column turns alerts off.
const sortField = ref(null);
const sortOrder = ref(null);

watch(showAlerts, (on) => {
    tableFirst.value = 0;
    if (on) sortField.value = null;
});

watch(sortField, (field) => {
    if (field) showAlerts.value = false;
});

const nav = useDrawerNavigation(displayedItems);
const selectedItem = computed(() => store.byId(nav.currentId));

function stockSeverity(item) {
    if (isNegativeStock(item)) return 'danger';
    if (isLowStock(item)) return 'warn';
    return null;
}

function rowClass(item) {
    return hasStockAlert(item) ? 'cursor-pointer stock-alert-row' : 'cursor-pointer';
}

function errorMessageFor(err) {
    if (err.status === 404) return 'El artículo no existe o fue desactivado.';
    if (err.status === 422) return 'Datos no válidos. Revisa los campos e intenta de nuevo.';
    return err.message ?? 'Ocurrió un error inesperado.';
}

function handleError(err) {
    if (handleAuthError(err)) return;
    toast.add({ severity: 'error', summary: 'Error', detail: errorMessageFor(err), life: 3000 });
}

onMounted(async () => {
    try {
        await store.load();
    } catch (err) {
        if (handleAuthError(err)) return;
        loadError.value = errorMessageFor(err);
    }
});

function onRowClick(event) {
    nav.open(event.data.id);
}

// --- Row actions ---

// Quantity typed in each row's field, by item id. A missing entry means the
// default of 1, and every action removes it so a leftover value can't be
// applied again by accident.
const stepByItemId = ref({});
const busyItemIds = ref(new Set());

function stepFor(item) {
    return stepByItemId.value[item.id] ?? 1;
}

function setStep(item, value) {
    stepByItemId.value[item.id] = value;
}

function isStepValid(item) {
    return isQuantityInRange(stepFor(item), 1);
}

async function runRowAction(item, action) {
    if (busyItemIds.value.has(item.id)) return;
    busyItemIds.value.add(item.id);
    try {
        await action();
    } catch (err) {
        handleError(err);
    } finally {
        busyItemIds.value.delete(item.id);
    }
}

async function applyMovement(item, type) {
    if (!isStepValid(item)) return;
    const quantity = stepFor(item);
    await runRowAction(item, () => store.addMovement(item.id, type, quantity));
    // Back to 1 even when the movement failed, so a retry can't reuse the
    // typed quantity without the owner typing it again.
    delete stepByItemId.value[item.id];
}

const countPopover = ref();
const countTarget = ref(null);
const countedQuantity = ref(null);

function openCount(event, item) {
    countTarget.value = item;
    countedQuantity.value = null;
    countPopover.value.toggle(event);
}

async function saveCount() {
    const item = countTarget.value;
    const counted = countedQuantity.value;
    if (!item || !isQuantityInRange(counted, 0)) return;
    countPopover.value.hide();
    await runRowAction(item, async () => {
        await store.count(item.id, counted);
        toast.add({ severity: 'success', summary: 'Conteo guardado', detail: `${item.name}: stock ajustado a ${counted}.`, life: 3000 });
    });
}

// --- Drawer ---

const newItem = ref({ name: '', quantity: 0, lowStockThreshold: null });
const submitted = ref(false);
const editableName = ref('');
const editableThreshold = ref(null);

watch(
    () => [nav.currentId, nav.visible],
    () => {
        newItem.value = { name: '', quantity: 0, lowStockThreshold: null };
        submitted.value = false;
        editableName.value = selectedItem.value?.name ?? '';
        editableThreshold.value = selectedItem.value?.low_stock_threshold ?? null;
        historyError.value = '';
    }
);

const isNameDirty = computed(() => {
    if (!selectedItem.value) return false;
    const name = editableName.value.trim();
    return name !== '' && name !== selectedItem.value.name;
});

const isThresholdDirty = computed(() => {
    if (!selectedItem.value || isOverCap(editableThreshold.value)) return false;
    return (editableThreshold.value ?? null) !== selectedItem.value.low_stock_threshold;
});

async function createItem() {
    submitted.value = true;
    const name = newItem.value.name.trim();
    const quantity = newItem.value.quantity;
    if (!name || !isQuantityInRange(quantity, 0) || isOverCap(newItem.value.lowStockThreshold)) return;
    try {
        await store.create(name, quantity, newItem.value.lowStockThreshold ?? null);
        toast.add({ severity: 'success', summary: 'Creado', detail: 'Artículo creado correctamente.', life: 3000 });
        nav.close();
    } catch (err) {
        handleError(err);
    }
}

async function saveName() {
    if (!isNameDirty.value) return;
    try {
        await store.update(selectedItem.value.id, { name: editableName.value.trim() });
        toast.add({ severity: 'success', summary: 'Guardado', detail: 'Nombre actualizado correctamente.', life: 3000 });
    } catch (err) {
        handleError(err);
    }
}

async function saveThreshold() {
    if (!isThresholdDirty.value) return;
    try {
        await store.update(selectedItem.value.id, { low_stock_threshold: editableThreshold.value ?? null });
        toast.add({ severity: 'success', summary: 'Guardado', detail: 'Umbral actualizado correctamente.', life: 3000 });
    } catch (err) {
        handleError(err);
    }
}

// History is fetched only while its panel is open. A movement drops the
// item's cached history in the store, which makes this run again and reload it.
const historyCollapsed = ref(true);
const historyError = ref('');
const selectedMovements = computed(() => store.movementsByItemId[nav.currentId]);

watch(
    () => [nav.visible, nav.currentId, historyCollapsed.value, selectedMovements.value],
    async () => {
        if (!nav.visible || nav.isNew || historyCollapsed.value || selectedMovements.value) return;
        const itemId = nav.currentId;
        historyError.value = '';
        try {
            await store.loadMovements(itemId);
        } catch (err) {
            if (handleAuthError(err)) return;
            if (nav.currentId === itemId) historyError.value = errorMessageFor(err);
        }
    }
);

const deactivateDialog = ref(false);

async function doDeactivate() {
    const item = selectedItem.value;
    deactivateDialog.value = false;
    if (!item) return;
    try {
        await store.deactivate(item.id);
        nav.close();
        toast.add({ severity: 'success', summary: 'Desactivado', detail: 'Artículo desactivado correctamente.', life: 3000 });
    } catch (err) {
        handleError(err);
    }
}
</script>

<template>
    <div>
        <div class="card">
            <Toolbar class="mb-6">
                <template #start>
                    <Button label="Nuevo artículo" icon="pi pi-plus" severity="secondary" @click="nav.openNew()" />
                </template>
            </Toolbar>

            <small v-if="loadError" class="text-red-500 block mb-4">{{ loadError }}</small>

            <DataTable :ref="nav.bindTable" v-model:first="tableFirst" v-model:sort-field="sortField" v-model:sort-order="sortOrder" :value="displayedItems" data-key="id" :row-class="rowClass" paginator :rows="30" row-hover @row-click="onRowClick">
                <template #header>
                    <div class="flex items-center justify-between flex-wrap gap-4">
                        <h4 class="m-0">Inventario</h4>
                        <div class="flex items-center gap-4">
                            <Button
                                :label="`Mostrar alertas (${store.alertItems.length})`"
                                icon="pi pi-exclamation-triangle"
                                severity="danger"
                                :outlined="!showAlerts"
                                @click="showAlerts = !showAlerts"
                            />
                            <InputText v-model="searchQuery" placeholder="Buscar por nombre..." />
                        </div>
                    </div>
                </template>

                <template #empty>
                    <span v-if="searchQuery.trim()">Ningún artículo coincide con la búsqueda.</span>
                    <span v-else>Aún no hay artículos. Usa "Nuevo artículo" para agregar el primero.</span>
                </template>

                <Column field="name" header="Nombre" sortable style="min-width: 16rem"></Column>
                <Column field="stock" header="Stock" sortable style="min-width: 8rem">
                    <template #body="slotProps">
                        <Tag v-if="stockSeverity(slotProps.data)" :severity="stockSeverity(slotProps.data)"><span class="text-base font-semibold">{{ slotProps.data.stock }}</span></Tag>
                        <span v-else class="text-base font-semibold">{{ slotProps.data.stock }}</span>
                    </template>
                </Column>
                <Column field="low_stock_threshold" header="Umbral" sortable style="min-width: 8rem">
                    <template #body="slotProps">
                        <span v-if="slotProps.data.low_stock_threshold !== null">{{ slotProps.data.low_stock_threshold }}</span>
                        <span v-else class="italic text-surface-500">Sin alerta</span>
                    </template>
                </Column>
                <Column header="Acciones" style="min-width: 22rem">
                    <template #body="slotProps">
                        <div class="flex items-center gap-2" @click.stop>
                            <Button v-tooltip.top="'Restar'" icon="pi pi-minus" outlined rounded severity="secondary" :disabled="!isStepValid(slotProps.data) || busyItemIds.has(slotProps.data.id)" @click="applyMovement(slotProps.data, 'exit')" />
                            <!-- InputNumber only commits its value on blur; @input keeps it current while typing, so buttons enabled by the value react right away. -->
                            <InputNumber
                                :model-value="stepFor(slotProps.data)"
                                :min="1"
                                :use-grouping="false"
                                :invalid="!isStepValid(slotProps.data)"
                                :aria-label="`Cantidad para ${slotProps.data.name}`"
                                input-class="w-16 text-center"
                                @update:model-value="(value) => setStep(slotProps.data, value)"
                                @input="(event) => setStep(slotProps.data, event.value)"
                            />
                            <Button v-tooltip.top="'Sumar'" icon="pi pi-plus" outlined rounded severity="secondary" :disabled="!isStepValid(slotProps.data) || busyItemIds.has(slotProps.data.id)" @click="applyMovement(slotProps.data, 'entry')" />
                            <Button label="Contar" icon="pi pi-calculator" text class="ml-4" :disabled="busyItemIds.has(slotProps.data.id)" @click="(event) => openCount(event, slotProps.data)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <Popover ref="countPopover">
            <div v-if="countTarget" class="flex flex-col gap-3 w-64">
                <span class="font-semibold">{{ countTarget.name }}</span>
                <small class="text-surface-500">Stock actual: {{ countTarget.stock }}</small>
                <label for="counted-quantity" class="font-bold">Cantidad contada</label>
                <InputNumber v-model="countedQuantity" input-id="counted-quantity" @input="(event) => (countedQuantity = event.value)" :min="0" :use-grouping="false" :invalid="isOverCap(countedQuantity)" autofocus fluid @keydown.enter="saveCount" />
                <small :class="isOverCap(countedQuantity) ? 'text-red-500' : 'text-surface-500'">Máximo {{ MAX_QUANTITY }} por conteo.</small>
                <Button label="Guardar" icon="pi pi-check" :disabled="!isQuantityInRange(countedQuantity, 0)" @click="saveCount" />
            </div>
        </Popover>

        <EntityDrawer :nav="nav" :header="nav.isNew ? 'Nuevo artículo' : 'Detalle del artículo'">
            <div v-if="nav.isNew" class="flex flex-col gap-6">
                <div>
                    <label for="item-new-name" class="block font-bold mb-3">Nombre</label>
                    <InputText id="item-new-name" v-model="newItem.name" :maxlength="MAX_NAME_LENGTH" autofocus :invalid="submitted && !newItem.name.trim()" fluid />
                    <small v-if="submitted && !newItem.name.trim()" class="text-red-500">El nombre es requerido.</small>
                </div>
                <div>
                    <label for="item-new-quantity" class="block font-bold mb-3">Cantidad inicial</label>
                    <InputNumber v-model="newItem.quantity" input-id="item-new-quantity" @input="(event) => (newItem.quantity = event.value)" :min="0" :use-grouping="false" :invalid="isOverCap(newItem.quantity) || (submitted && !Number.isInteger(newItem.quantity))" fluid />
                    <small v-if="isOverCap(newItem.quantity)" class="text-red-500">Máximo {{ MAX_QUANTITY }}.</small>
                    <small v-else-if="submitted && !Number.isInteger(newItem.quantity)" class="text-red-500">La cantidad es requerida.</small>
                </div>
                <div>
                    <label for="item-new-threshold" class="block font-bold mb-3">Umbral de stock bajo</label>
                    <InputNumber v-model="newItem.lowStockThreshold" input-id="item-new-threshold" @input="(event) => (newItem.lowStockThreshold = event.value)" :min="0" :use-grouping="false" :invalid="isOverCap(newItem.lowStockThreshold)" placeholder="Sin alerta" fluid />
                    <small v-if="isOverCap(newItem.lowStockThreshold)" class="text-red-500 block mt-2">Máximo {{ MAX_QUANTITY }}.</small>
                    <small class="text-surface-500 block mt-2">Opcional. Si lo dejas vacío, este artículo no tendrá alerta de stock bajo.</small>
                </div>
            </div>

            <div v-else-if="selectedItem" class="flex flex-col gap-6">
                <div>
                    <label class="block font-bold mb-3">Stock actual</label>
                    <Tag v-if="stockSeverity(selectedItem)" :severity="stockSeverity(selectedItem)"><span class="text-base font-semibold">{{ selectedItem.stock }}</span></Tag>
                    <span v-else class="text-base font-semibold">{{ selectedItem.stock }}</span>
                </div>

                <div>
                    <label for="item-name" class="block font-bold mb-3">Nombre</label>
                    <InputText id="item-name" v-model="editableName" :maxlength="MAX_NAME_LENGTH" fluid @keyup.enter="saveName" />
                    <Button label="Guardar" icon="pi pi-check" class="mt-3" :disabled="!isNameDirty" @click="saveName" />
                </div>

                <div>
                    <label for="item-threshold" class="block font-bold mb-3">Umbral de stock bajo</label>
                    <InputNumber v-model="editableThreshold" input-id="item-threshold" @input="(event) => (editableThreshold = event.value)" :min="0" :use-grouping="false" :invalid="isOverCap(editableThreshold)" placeholder="Sin alerta" fluid @keydown.enter="saveThreshold" />
                    <small v-if="isOverCap(editableThreshold)" class="text-red-500 block mt-2">Máximo {{ MAX_QUANTITY }}.</small>
                    <small class="text-surface-500 block mt-2">Si lo dejas vacío, este artículo no tendrá alerta de stock bajo.</small>
                    <Button label="Guardar" icon="pi pi-check" class="mt-3" :disabled="!isThresholdDirty" @click="saveThreshold" />
                </div>

                <Panel v-model:collapsed="historyCollapsed" header="Historial de movimientos" toggleable>
                    <small v-if="historyError" class="text-red-500">{{ historyError }}</small>
                    <div v-else-if="!selectedMovements" class="flex justify-center py-4">
                        <ProgressSpinner style="width: 32px; height: 32px" />
                    </div>
                    <div v-else-if="selectedMovements.length === 0" class="italic text-surface-500">Sin movimientos.</div>
                    <ul v-else class="flex flex-col gap-3 max-h-96 overflow-y-auto m-0 p-0 list-none">
                        <li v-for="movement in selectedMovements" :key="movement.id" class="flex flex-col gap-1 pb-3 border-b border-surface">
                            <div class="flex items-center justify-between gap-4">
                                <span class="font-semibold">{{ movementTypeLabel(movement.type) }}</span>
                                <span :class="movement.quantity < 0 ? 'text-red-500' : 'text-green-600'">{{ movement.quantity > 0 ? `+${movement.quantity}` : movement.quantity }}</span>
                            </div>
                            <small class="text-surface-500">{{ formatDate(movement.created_at) }}</small>
                            <small v-if="movement.note">{{ movement.note }}</small>
                        </li>
                    </ul>
                </Panel>

                <Button label="Desactivar" icon="pi pi-trash" severity="danger" outlined @click="deactivateDialog = true" />
            </div>

            <template v-if="nav.isNew" #footer>
                <div class="flex justify-end gap-2">
                    <Button label="Cancelar" icon="pi pi-times" text @click="nav.close()" />
                    <Button label="Guardar" icon="pi pi-check" @click="createItem" />
                </div>
            </template>
        </EntityDrawer>

        <Dialog v-model:visible="deactivateDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle text-3xl!" />
                <span v-if="selectedItem"
                    >¿Desactivar <b>{{ selectedItem.name }}</b
                    >? Desaparecerá del inventario y no se puede deshacer desde la aplicación.</span
                >
            </div>
            <template #footer>
                <Button label="No" icon="pi pi-times" text @click="deactivateDialog = false" />
                <Button label="Sí, desactivar" icon="pi pi-check" severity="danger" @click="doDeactivate" />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
:deep(.p-datatable-tbody > tr.stock-alert-row) {
    background: linear-gradient(90deg, color-mix(in srgb, var(--p-red-500) 22%, transparent), transparent 75%);
}
</style>

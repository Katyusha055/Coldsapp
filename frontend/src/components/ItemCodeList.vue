<script setup>
import { ref } from 'vue';
import { useToast } from 'primevue/usetoast';

// An item's codes, each with copy-as-number, copy-as-image and remove. Used
// by both drawers (the inventory page's and the scan view's phone drawer).

defineProps({
    codes: { type: Array, required: true },
    // Disables "Quitar" while the drawer has a request in flight.
    busy: { type: Boolean, default: false },
    // Larger text for the phone drawer.
    large: { type: Boolean, default: false }
});
const emit = defineEmits(['remove']);

const toast = useToast();
const renderingCode = ref(null);

// "Quitar" asks first: it sits right next to the copy buttons, and if the
// label is worn, this list may be the only place the number was written down.
const codePendingRemoval = ref(null);

function confirmRemove() {
    const code = codePendingRemoval.value;
    codePendingRemoval.value = null;
    if (code) emit('remove', code);
}

async function copyNumber(code) {
    try {
        await navigator.clipboard.writeText(code);
        toast.add({ severity: 'success', summary: 'Número copiado', detail: code, life: 2000 });
    } catch {
        toast.add({ severity: 'error', summary: 'No se pudo copiar', detail: 'Selecciona el número y cópialo a mano.', life: 4000 });
    }
}

function downloadPng(blob, code) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `codigo-${code}.png`;
    link.click();
    // Revoked a moment later: revoking right away can cancel the download.
    setTimeout(() => URL.revokeObjectURL(url), 10000);
}

async function copyImage(code) {
    renderingCode.value = code;
    // The PNG goes to ClipboardItem as a promise, created right in the tap:
    // Safari only allows clipboard writes started synchronously by the user.
    const png = import('@/utils/barcodeWriter.js').then((writer) => writer.renderBarcodePng(code));
    try {
        if (!window.ClipboardItem || !navigator.clipboard?.write) throw new Error('Image clipboard not supported');
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': png })]);
        toast.add({ severity: 'success', summary: 'Imagen copiada', detail: 'Pégala en un documento o en el programa de etiquetas para imprimirla.', life: 4000 });
    } catch {
        // No image clipboard (or it was refused): download the PNG instead,
        // which serves printing just as well.
        try {
            downloadPng(await png, code);
            toast.add({ severity: 'info', summary: 'Imagen descargada', detail: 'Tu navegador no permite copiar imágenes, así que se descargó como archivo.', life: 5000 });
        } catch {
            toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo generar la imagen del código.', life: 4000 });
        }
    } finally {
        renderingCode.value = null;
    }
}
</script>

<template>
    <span v-if="codes.length === 0" class="italic text-surface-500">Sin códigos.</span>
    <ul v-else class="flex flex-col gap-2 m-0 p-0 list-none">
        <li v-for="code in codes" :key="code" class="flex items-center justify-between gap-2">
            <span class="font-mono" :class="{ 'text-lg': large }">{{ code }}</span>
            <div class="flex items-center gap-1">
                <Button v-tooltip.top="'Copiar número'" icon="pi pi-copy" text rounded severity="secondary" aria-label="Copiar número" @click="copyNumber(code)" />
                <Button v-tooltip.top="'Copiar imagen del código'" icon="pi pi-image" text rounded severity="secondary" aria-label="Copiar imagen del código" :loading="renderingCode === code" @click="copyImage(code)" />
                <Button v-tooltip.top="'Quitar'" icon="pi pi-times" text rounded severity="danger" aria-label="Quitar código" :disabled="busy" @click="codePendingRemoval = code" />
            </div>
        </li>
    </ul>

    <Dialog :visible="codePendingRemoval !== null" header="Confirmar" :modal="true" :style="{ width: '26rem', maxWidth: '90vw' }" @update:visible="(value) => !value && (codePendingRemoval = null)">
        <div class="flex items-center gap-4">
            <i class="pi pi-exclamation-triangle text-3xl!" />
            <span
                >¿Quitar el código <b class="font-mono">{{ codePendingRemoval }}</b> de este artículo? Si la etiqueta ya no se puede leer, anota o copia el número antes de quitarlo.</span
            >
        </div>
        <template #footer>
            <Button label="No" icon="pi pi-times" text @click="codePendingRemoval = null" />
            <Button label="Sí, quitar" icon="pi pi-check" severity="danger" @click="confirmRemove" />
        </template>
    </Dialog>
</template>

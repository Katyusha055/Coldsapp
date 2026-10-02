<script setup>
defineProps({
    header: { type: String, default: '' },
    nav: { type: Object, required: true }
});
</script>

<template>
    <Drawer :visible="nav.visible" position="right" @update:visible="(value) => !value && nav.close()" :style="{ width: '28rem' }">
        <template #header>
            <div class="flex items-center justify-between w-full gap-4">
                <span class="font-semibold text-xl">{{ header }}</span>
                <div v-if="!nav.isNew" class="flex items-center gap-1">
                    <Button icon="pi pi-chevron-up" text rounded severity="secondary" :disabled="!nav.hasPrev" v-tooltip.bottom="'Anterior'" @click="nav.prev()" />
                    <small class="text-surface-500 whitespace-nowrap">{{ nav.position }}</small>
                    <Button icon="pi pi-chevron-down" text rounded severity="secondary" :disabled="!nav.hasNext" v-tooltip.bottom="'Siguiente'" @click="nav.next()" />
                </div>
            </div>
        </template>

        <slot />

        <template v-if="$slots.footer" #footer>
            <slot name="footer" />
        </template>
    </Drawer>
</template>

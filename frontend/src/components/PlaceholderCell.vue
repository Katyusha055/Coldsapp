<script setup>
defineProps({
    value: { type: String, default: null },
    placeholder: { type: String, required: true },
    truncate: { type: Boolean, default: false }
});
</script>

<template>
    <span v-if="value" v-tooltip.top="truncate ? value : null" :class="{ 'block truncate': truncate }">{{ value }}</span>
    <span v-else class="italic text-surface-500">{{ placeholder }}</span>
</template>

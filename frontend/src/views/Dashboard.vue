<script setup>
import ContactWidget from '@/components/dashboard/ContactWidget.vue';
import TopClientsWidget from '@/components/dashboard/TopClientsWidget.vue';
import PendingTicketsWidget from '@/components/dashboard/PendingTicketsWidget.vue';
</script>

<template>
    <div class="grid grid-cols-12 gap-8">
        <div class="col-span-12">
            <ContactWidget />
        </div>
        <div class="col-span-12 xl:col-span-6">
            <TopClientsWidget />
        </div>
        <div class="col-span-12 xl:col-span-6">
            <PendingTicketsWidget />
        </div>
    </div>
</template>

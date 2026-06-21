<script setup>
</script>

<template>
    <Card>
        <template #title>Contacto de Soporte</template>
        <template #content>
            <div class="flex flex-col gap-4">
                <div class="flex items-center gap-2">
                    <i class="pi pi-phone text-primary" />
                    <span class="text-lg font-medium">+593 000 000 000</span>
                </div>
                <div>
                    <Button
                        label="Abrir WhatsApp"
                        icon="pi pi-whatsapp"
                        :disabled="true"
                        v-tooltip.right="'Próximamente'"
                    />
                </div>
            </div>
        </template>
    </Card>
</template>

import { createEntityStore } from '@/stores/createEntityStore.js';
import { getPendingContacts, updatePendingStatus, deletePending } from '@/services/WhatsappService.js';

export const usePendingsStore = createEntityStore('pendings', {
    fetchAll: getPendingContacts,

    actions: {
        // The list only holds contacts still pending, so converting or
        // discarding one takes it out.
        async resolve(id, status) {
            await updatePendingStatus(id, status);
            this.removeOne(id);
        },

        async remove(id) {
            await deletePending(id);
            this.removeOne(id);
        }
    }
});

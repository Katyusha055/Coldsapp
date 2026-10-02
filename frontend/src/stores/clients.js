import { createEntityStore } from '@/stores/createEntityStore.js';
import { getClients, createClient, updateClient, deleteClient } from '@/services/ClientService.js';

export const useClientsStore = createEntityStore('clients', {
    fetchAll: getClients,

    actions: {
        async create(data) {
            const created = await createClient(data);
            this.upsertOne(created);
            return created;
        },

        async update(id, data) {
            const updated = await updateClient(id, data);
            this.upsertOne(updated);
            return updated;
        },

        async remove(id) {
            await deleteClient(id);
            this.removeOne(id);
        }
    }
});

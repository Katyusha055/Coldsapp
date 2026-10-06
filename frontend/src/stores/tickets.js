import { createEntityStore } from '@/stores/createEntityStore.js';
import { getTickets, createTicket, updateTicket, updateTicketStatus, deleteTicket } from '@/services/TicketService.js';

export const useTicketsStore = createEntityStore('tickets', {
    fetchAll: getTickets,

    actions: {
        async create(clientId, title, description) {
            const created = await createTicket(clientId, title, description);
            this.upsertOne(created);
            return created;
        },

        async update(id, title, description) {
            const updated = await updateTicket(id, title, description);
            this.upsertOne(updated);
            return updated;
        },

        async setStatus(id, status) {
            const updated = await updateTicketStatus(id, status);
            this.upsertOne(updated);
            return updated;
        },

        async remove(id) {
            await deleteTicket(id);
            this.removeOne(id);
        }
    }
});

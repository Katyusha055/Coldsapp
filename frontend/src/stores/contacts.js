import { createEntityStore } from '@/stores/createEntityStore.js';
import { fetchContacts, triggerImport, updateContactName, updateContactOptedOut } from '@/services/ContactService.js';

export const useContactsStore = createEntityStore('contacts', {
    fetchAll: fetchContacts,

    getters: {
        activeContacts: (state) => state.items.filter((contact) => contact.opted_out === false),
        blacklistedContacts: (state) => state.items.filter((contact) => contact.opted_out === true)
    },

    actions: {
        async refresh() {
            await this._withLoading(async () => {
                await triggerImport();
                await this._fetchInto();
            });
        },

        async updateName(id, name) {
            await updateContactName(id, name);
            this.upsertOne({ id, name });
        },

        async toggleOptedOut(id, optedOut) {
            await updateContactOptedOut(id, optedOut);
            this.upsertOne({ id, opted_out: optedOut });
        }
    }
});

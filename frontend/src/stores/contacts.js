import { defineStore } from 'pinia';
import { fetchContacts, triggerImport, updateContactName, updateContactOptedOut } from '@/services/ContactService.js';

export const useContactsStore = defineStore('contacts', {
    state: () => ({
        contacts: [],
        loaded: false,
        loading: false,
        error: null
    }),

    getters: {
        activeContacts: (state) => state.contacts.filter((contact) => contact.opted_out === false),
        blacklistedContacts: (state) => state.contacts.filter((contact) => contact.opted_out === true)
    },

    actions: {
        async _withLoading(work) {
            this.loading = true;
            this.error = null;
            try {
                await work();
            } catch (err) {
                this.error = err.message;
                throw err;
            } finally {
                this.loading = false;
            }
        },

        async loadContacts(force = false) {
            if (this.loaded && !force) return;
            await this._withLoading(async () => {
                this.contacts = await fetchContacts();
                this.loaded = true;
            });
        },

        async refresh() {
            await this._withLoading(async () => {
                await triggerImport();
                this.contacts = await fetchContacts();
                this.loaded = true;
            });
        },

        async updateName(id, name) {
            await updateContactName(id, name);
            const contact = this.contacts.find((c) => c.id === id);
            if (contact) contact.name = name;
        },

        async toggleOptedOut(id, optedOut) {
            await updateContactOptedOut(id, optedOut);
            const contact = this.contacts.find((c) => c.id === id);
            if (contact) contact.opted_out = optedOut;
        }
    }
});

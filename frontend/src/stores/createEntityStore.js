import { defineStore } from 'pinia';

const registry = [];

// Bumped on every reset so a fetch that was in flight during logout can't
// write the previous session's rows into the freshly reset store.
let generation = 0;

export function createEntityStore(name, { fetchAll, getters = {}, actions = {} }) {
    let inFlight = null;

    const useStore = defineStore(name, {
        state: () => ({
            items: [],
            loaded: false,
            loading: false,
            error: null
        }),

        getters: {
            byId: (state) => (id) => state.items.find((item) => item.id === id),
            ...getters
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

            async _fetchInto() {
                const startedAt = generation;
                const items = await fetchAll();
                if (startedAt === generation) this.setAll(items);
            },

            async load(force = false) {
                if (this.loaded && !force) return;
                if (inFlight?.generation === generation) return inFlight.promise;
                const request = { generation };
                request.promise = this._withLoading(() => this._fetchInto()).finally(() => {
                    if (inFlight === request) inFlight = null;
                });
                inFlight = request;
                return request.promise;
            },

            setAll(items) {
                this.items = items;
                this.loaded = true;
            },

            upsertOne(item) {
                const existing = this.items.find((entry) => entry.id === item.id);
                if (existing) Object.assign(existing, item);
                else this.items.push(item);
            },

            removeOne(id) {
                this.items = this.items.filter((item) => item.id !== id);
            },

            invalidate() {
                this.loaded = false;
            },

            ...actions
        }
    });

    registry.push(useStore);
    return useStore;
}

export function resetAllStores() {
    generation += 1;
    registry.forEach((useStore) => useStore().$reset());
}

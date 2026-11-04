import { createEntityStore } from '@/stores/createEntityStore.js';
import { getItems, createItem, updateItem, deactivateItem, addMovement, getMovements, countItem } from '@/services/InventoryService.js';

export const useInventoryStore = createEntityStore('inventory', {
    fetchAll: getItems,

    // History per item id, fetched the first time an item's history is opened.
    // A movement drops that item's entry: the API returns the item, not the
    // new movement, so the cached list can't be appended to.
    state: () => ({ movementsByItemId: {} }),

    actions: {
        async create(name, quantity) {
            const created = await createItem(name, quantity);
            this.upsertOne(created);
            return created;
        },

        async update(id, data) {
            const updated = await updateItem(id, data);
            this.upsertOne(updated);
            return updated;
        },

        async deactivate(id) {
            await deactivateItem(id);
            this.removeOne(id);
            delete this.movementsByItemId[id];
        },

        async addMovement(id, type, quantity, note = null) {
            const updated = await addMovement(id, type, quantity, note);
            this.upsertOne(updated);
            delete this.movementsByItemId[id];
            return updated;
        },

        async count(id, counted) {
            const updated = await countItem(id, counted);
            this.upsertOne(updated);
            delete this.movementsByItemId[id];
            return updated;
        },

        async loadMovements(id) {
            if (this.movementsByItemId[id]) return;
            const movements = await getMovements(id);
            // After a logout reset the item is gone, so a late response is dropped.
            if (this.byId(id)) this.movementsByItemId[id] = movements;
        }
    }
});

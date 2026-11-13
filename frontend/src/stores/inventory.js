import { createEntityStore } from '@/stores/createEntityStore.js';
import { getItems, getItem, createItem, updateItem, deactivateItem, addMovement, getMovements, countItem } from '@/services/InventoryService.js';
import { linkCode, unlinkCode } from '@/services/BarcodeService.js';

export function isNegativeStock(item) {
    return item.stock < 0;
}

// A NULL threshold means the item never alerts; 0 alerts when it runs out.
export function isLowStock(item) {
    return item.low_stock_threshold !== null && item.stock <= item.low_stock_threshold;
}

export function hasStockAlert(item) {
    return isNegativeStock(item) || isLowStock(item);
}

export const useInventoryStore = createEntityStore('inventory', {
    fetchAll: getItems,

    getters: {
        alertItems: (state) => state.items.filter(hasStockAlert)
    },

    // History per item id, fetched the first time an item's history is opened.
    // A movement drops that item's entry: the API returns the item, not the
    // new movement, so the cached list can't be appended to.
    state: () => ({ movementsByItemId: {} }),

    actions: {
        async create(name, quantity, lowStockThreshold = null, code = null) {
            const created = await createItem(name, quantity, lowStockThreshold, code);
            this.upsertOne(created);
            return created;
        },

        // Fetches the items again even if already loaded, since stock may have
        // changed from another device (the phone's scan view). Cached histories
        // are dropped too: they would be just as stale.
        async refresh() {
            this.movementsByItemId = {};
            await this.load(true);
        },

        async linkCode(id, code) {
            const updated = await linkCode(id, code);
            this.upsertOne(updated);
            return updated;
        },

        // The API answers 204 with no item, so the code is dropped from the
        // cached one. code is the normalized form taken from item.codes.
        //
        // A 404 means the cached item is stale: the code was already unlinked,
        // or the item deactivated, on another device. The item is fetched
        // again so the view shows its current state, then the error is
        // rethrown with err.alreadyUnlinked or err.itemGone for the message.
        async unlinkCode(id, code) {
            try {
                await unlinkCode(id, code);
            } catch (err) {
                if (err.status !== 404) throw err;
                try {
                    this.upsertOne(await getItem(id));
                    err.alreadyUnlinked = true;
                } catch (refetchErr) {
                    if (refetchErr.status !== 404) throw err;
                    this.removeOne(id);
                    delete this.movementsByItemId[id];
                    err.itemGone = true;
                }
                throw err;
            }
            const item = this.byId(id);
            if (item) item.codes = item.codes.filter((linked) => linked !== code);
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

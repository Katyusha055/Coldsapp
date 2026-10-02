import { computed, reactive, ref, toValue } from 'vue';

export function useDrawerNavigation(fallbackRows) {
    let table = null;
    const visible = ref(false);
    const currentId = ref(null);
    const orderedIds = ref([]);

    const index = computed(() => orderedIds.value.indexOf(currentId.value));
    const isNew = computed(() => currentId.value === null);
    const hasPrev = computed(() => index.value > 0);
    const hasNext = computed(() => index.value !== -1 && index.value < orderedIds.value.length - 1);
    const position = computed(() => (index.value === -1 ? '' : `${index.value + 1} / ${orderedIds.value.length}`));

    function bindTable(instance) {
        table = instance;
    }

    // The order is frozen when the drawer opens: editing a record can re-sort
    // or filter it out of the table, and "next" must not jump because of that.
    // processedData is DataTable's own sorted list across all pages; its
    // value-change event only fires on sort clicks and page changes, so it
    // can't supply the order on first open or after a search.
    function open(id) {
        const rows = table?.processedData ?? toValue(fallbackRows) ?? [];
        orderedIds.value = rows.map((row) => row.id);
        currentId.value = id;
        visible.value = true;
    }

    function openNew() {
        orderedIds.value = [];
        currentId.value = null;
        visible.value = true;
    }

    function close() {
        visible.value = false;
    }

    function prev() {
        if (hasPrev.value) currentId.value = orderedIds.value[index.value - 1];
    }

    function next() {
        if (hasNext.value) currentId.value = orderedIds.value[index.value + 1];
    }

    return reactive({ visible, currentId, isNew, hasPrev, hasNext, position, bindTable, open, openNew, close, prev, next });
}

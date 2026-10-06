import { onMounted, onUnmounted } from 'vue';
import { BASE_URL } from '@/services/api.js';
import { getToken } from '@/services/AuthService.js';
import { usePendingsStore } from '@/stores/pendings.js';

export function useWhatsappEvents({ onConnectionUpdate, onQrUpdated }) {
    const pendingsStore = usePendingsStore();
    let source = null;

    function handle(data) {
        if (data.type === 'new_pending') {
            pendingsStore.upsertOne({
                id: data.id,
                remote_jid: data.remote_jid,
                name: data.name,
                last_message: data.message,
                last_message_at: new Date().toISOString()
            });
        } else if (data.type === 'pending_update') {
            pendingsStore.upsertOne({
                id: data.id,
                remote_jid: data.remote_jid,
                last_message: data.message,
                last_message_at: new Date().toISOString()
            });
        } else if (data.type === 'connection_update') {
            onConnectionUpdate(data.detail);
        } else if (data.type === 'qr_updated') {
            onQrUpdated();
        }
    }

    onMounted(() => {
        source = new EventSource(`${BASE_URL}/whatsapp/events?token=${getToken()}`);
        source.onmessage = (event) => handle(JSON.parse(event.data));
    });

    onUnmounted(() => {
        source?.close();
        source = null;
        // Nothing keeps the list current once the stream is closed.
        pendingsStore.invalidate();
    });
}

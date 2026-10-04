export function formatDate(value) {
    if (!value) return '';
    return new Date(value).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

const TICKET_STATUS_LABELS = {
    pending: 'Pendiente',
    in_progress: 'En progreso',
    ready: 'Listo',
    delivered: 'Entregado',
    cancelled: 'Cancelado'
};

export function ticketStatusLabel(status) {
    return TICKET_STATUS_LABELS[status] ?? status;
}

export function formatPhone(remoteJid) {
    if (!remoteJid) return '';
    return `+${remoteJid.split('@')[0]}`;
}

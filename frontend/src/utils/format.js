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

// Ecuadorian mobile JIDs only: 593 + 9 digits becomes the 10-digit local
// form clients are stored in. Anything else (foreign numbers, @lid privacy
// ids) has no correct local form, so it returns ''.
export function localPhoneFromJid(remoteJid) {
    const match = /^593(\d{9})@s\.whatsapp\.net$/.exec(remoteJid ?? '');
    return match ? `0${match[1]}` : '';
}

export function formatPhone(remoteJid) {
    if (!remoteJid) return '';
    return `+${remoteJid.split('@')[0]}`;
}

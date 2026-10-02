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

export function formatPhone(remoteJid) {
    if (!remoteJid) return '';
    return `+${remoteJid.split('@')[0]}`;
}

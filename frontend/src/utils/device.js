// True on phones and tablets: their main pointer is a finger. Used to tell a
// phone from a PC without parsing the user agent; a PC with a touch screen
// whose main pointer is a mouse counts as a PC.
export function hasTouchScreen() {
    return window.matchMedia?.('(pointer: coarse)').matches ?? false;
}

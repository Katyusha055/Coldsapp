import { ref, onBeforeUnmount } from 'vue';
import { readRetailBarcode } from '@/utils/barcodeReader.js';

// About 7 decode attempts per second. Each attempt waits for the previous one,
// so a slow phone decodes less often instead of piling calls up.
const FRAME_INTERVAL_MS = 140;
// A code is accepted when the same text is read twice within this window. In
// the camera test reads arrived intermittently, so requiring two consecutive
// frames added seconds; twice within ~1 s still guards against a one-frame
// misread.
const CONFIRM_WINDOW_MS = 1000;

const VIDEO_SIZE = { width: { ideal: 1920 }, height: { ideal: 1080 } };

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function cameraErrorMessage(err) {
    if (err.name === 'NotAllowedError') return 'Permiso de cámara denegado. Actívalo en la configuración del navegador o escribe el código.';
    if (err.name === 'NotFoundError' || err.name === 'OverconstrainedError') return 'No se encontró una cámara. Abre Coldsapp en tu celular para escanear, o escribe el código.';
    if (err.name === 'NotReadableError') return 'La cámara está siendo usada por otra aplicación.';
    return 'No se pudo abrir la cámara.';
}

// videoElement: a template ref to the <video> that shows the camera.
export function useBarcodeScanner(videoElement) {
    const cameras = ref([]);
    const activeDeviceId = ref(null);
    const starting = ref(false);
    const scanning = ref(false);
    const paused = ref(false);
    const torchSupported = ref(false);
    const torchOn = ref(false);
    const error = ref('');
    const result = ref(null);

    let stream = null;
    let track = null;
    // Bumped by every start and stop: a loop or a pending start from an older
    // run sees the change and ends, so a closed camera never comes back.
    let runId = 0;
    // Set when the view unmounts. A start requested after that (for example
    // by a failed lookup that comes back late) must not open the camera: no
    // unmount hook would ever close it again.
    let disposed = false;

    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d', { willReadFrequently: true });

    function stop() {
        runId += 1;
        starting.value = false;
        scanning.value = false;
        torchOn.value = false;
        torchSupported.value = false;
        stream?.getTracks().forEach((mediaTrack) => mediaTrack.stop());
        stream = null;
        track = null;
        if (videoElement.value) videoElement.value.srcObject = null;
    }

    async function start(deviceId = null) {
        if (disposed) return;
        stop();
        const thisRun = ++runId;
        error.value = '';
        result.value = null;
        paused.value = false;

        if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
            error.value = 'La cámara necesita una conexión segura (HTTPS). Abre Coldsapp en tu celular para escanear, o escribe el código.';
            return;
        }

        starting.value = true;
        const video = deviceId ? { deviceId: { exact: deviceId }, ...VIDEO_SIZE } : { facingMode: { ideal: 'environment' }, ...VIDEO_SIZE };
        let newStream;
        try {
            newStream = await navigator.mediaDevices.getUserMedia({ audio: false, video });
        } catch (err) {
            if (thisRun === runId) {
                starting.value = false;
                error.value = cameraErrorMessage(err);
            }
            return;
        }
        if (thisRun !== runId || disposed) {
            newStream.getTracks().forEach((mediaTrack) => mediaTrack.stop());
            return;
        }

        stream = newStream;
        track = stream.getVideoTracks()[0];
        activeDeviceId.value = track.getSettings?.().deviceId ?? deviceId;
        const element = videoElement.value;
        element.srcObject = stream;
        await element.play().catch(() => {});
        await applyBestEffortSettings();
        await listCameras();
        if (thisRun !== runId) return;

        starting.value = false;
        scanning.value = true;
        decodeLoop(thisRun);
    }

    // Continuous autofocus and the torch only where the camera reports them;
    // anything unsupported is skipped, never an error.
    async function applyBestEffortSettings() {
        const capabilities = track.getCapabilities?.() ?? {};
        if (Array.isArray(capabilities.focusMode) && capabilities.focusMode.includes('continuous')) {
            try {
                await track.applyConstraints({ advanced: [{ focusMode: 'continuous' }] });
            } catch {
                // keep the camera's default focus
            }
        }
        torchSupported.value = Boolean(capabilities.torch);
    }

    // Labels are only filled in after camera permission is granted.
    async function listCameras() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            cameras.value = devices.filter((device) => device.kind === 'videoinput').map((device, index) => ({ deviceId: device.deviceId, label: device.label || `Cámara ${index + 1}` }));
        } catch {
            cameras.value = [];
        }
    }

    async function toggleTorch() {
        if (!track) return;
        const next = !torchOn.value;
        try {
            await track.applyConstraints({ advanced: [{ torch: next }] });
            torchOn.value = next;
        } catch {
            torchSupported.value = false;
        }
    }

    async function decodeLoop(thisRun) {
        let lastText = null;
        let lastReadAt = 0;
        while (thisRun === runId) {
            const frameStartedAt = performance.now();
            const element = videoElement.value;
            if (element?.videoWidth && element.videoHeight) {
                if (canvas.width !== element.videoWidth || canvas.height !== element.videoHeight) {
                    canvas.width = element.videoWidth;
                    canvas.height = element.videoHeight;
                }
                context.drawImage(element, 0, 0, canvas.width, canvas.height);
                const imageData = context.getImageData(0, 0, canvas.width, canvas.height);

                let text;
                try {
                    text = await readRetailBarcode(imageData);
                } catch (err) {
                    // The reader failed to load or crashed: stop instead of retrying every frame.
                    console.error(err);
                    if (thisRun === runId) {
                        stop();
                        error.value = 'No se pudo cargar el lector de códigos. Recarga la página o escribe el código.';
                    }
                    return;
                }
                if (thisRun !== runId) return;

                if (text) {
                    const now = performance.now();
                    if (text === lastText && now - lastReadAt <= CONFIRM_WINDOW_MS) {
                        stop();
                        result.value = text;
                        return;
                    }
                    lastText = text;
                    lastReadAt = now;
                }
            }
            const waitMs = FRAME_INTERVAL_MS - (performance.now() - frameStartedAt);
            if (waitMs > 0) await sleep(waitMs);
        }
    }

    // A hidden page (another app, a locked screen) turns the camera off; the
    // view offers to resume.
    function onVisibilityChange() {
        if (document.hidden && (starting.value || scanning.value)) {
            stop();
            paused.value = true;
        }
    }

    document.addEventListener('visibilitychange', onVisibilityChange);

    onBeforeUnmount(() => {
        disposed = true;
        document.removeEventListener('visibilitychange', onVisibilityChange);
        stop();
    });

    return { cameras, activeDeviceId, starting, scanning, paused, torchSupported, torchOn, error, result, start, stop, toggleTorch };
}

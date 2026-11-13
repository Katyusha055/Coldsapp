import { prepareZXingModule, writeBarcode } from 'zxing-wasm/writer';
// The writer's .wasm is bundled and served from Coldsapp's own origin, like the
// reader's (see barcodeReader.js). Import this module dynamically: only copying
// a code's image needs it, so nobody else downloads it.
import writerWasmUrl from 'zxing-wasm/writer/zxing_writer.wasm?url';

prepareZXingModule({
    overrides: {
        locateFile: (path, prefix) => (path.endsWith('.wasm') ? writerWasmUrl : prefix + path)
    }
});

// code is a stored code: always a valid 13-digit EAN-13 (a UPC-A is stored
// with its leading 0, and still scans as the same product). The PNG has the
// digits printed under the bars, as on a real label.
export async function renderBarcodePng(code) {
    const output = await writeBarcode(code, { format: 'EAN13', scale: 4, addHRT: true });
    if (output.error || !output.image) throw new Error(output.error || 'No image');
    return output.image;
}

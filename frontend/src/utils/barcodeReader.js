import { prepareZXingModule, readBarcodes } from 'zxing-wasm/reader';
// The reader's .wasm is bundled and served from Coldsapp's own origin. Without
// this, zxing-wasm downloads it from jsDelivr. It must match the package
// version, which package.json pins exactly.
import readerWasmUrl from 'zxing-wasm/reader/zxing_reader.wasm?url';

prepareZXingModule({
    overrides: {
        locateFile: (path, prefix) => (path.endsWith('.wasm') ? readerWasmUrl : prefix + path)
    }
});

// Only EAN-13 and UPC-A are stored (S2). A UPC-A comes back as 13 digits with
// a leading 0, which is already the server's canonical form.
const READER_OPTIONS = {
    formats: ['EAN13', 'UPCA'],
    tryHarder: true,
    maxNumberOfSymbols: 1
};

// Returns the decoded text of the first valid barcode in the frame, or null.
export async function readRetailBarcode(imageData) {
    const results = await readBarcodes(imageData, READER_OPTIONS);
    return results.find((result) => result.isValid)?.text ?? null;
}

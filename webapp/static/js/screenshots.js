// Screenshots arrive over the socket as binary chunks and are kept in this browser tab only.
// They are shown in the gallery and zipped here; the server keeps nothing.
import { $, show } from './dom.js';

const shots = new Map();       // filename -> { blob, url }
const incoming = new Map();    // "jobId/filename" -> { parts, received }

export function receiveChunk({ job_id, filename, chunk, chunk_index, total_chunks }) {
    const key = `${job_id}/${filename}`;
    if (!incoming.has(key)) {
        incoming.set(key, { parts: new Array(total_chunks), received: 0 });
    }
    const pending = incoming.get(key);
    pending.parts[chunk_index] = chunk;
    pending.received++;
    if (pending.received < total_chunks) {
        return;
    }
    incoming.delete(key);

    const blob = new Blob(pending.parts, { type: 'image/png' });
    const url = URL.createObjectURL(blob);
    shots.set(filename, { blob, url });
    addToGallery(filename, url);
}

function addToGallery(filename, url) {
    const grid = $('screenshotsGrid');
    show('screenshotsGallery');

    const item = document.createElement('div');
    item.className = 'screenshot-item';
    item.addEventListener('click', () => openModal(url));
    const img = document.createElement('img');
    img.src = url;
    img.alt = filename;
    img.loading = 'lazy';
    item.appendChild(img);
    grid.appendChild(item);

    $('screenshotCount').textContent = `${grid.children.length} screenshots`;
}

export function screenshotCount() {
    return $('screenshotsGrid').children.length;
}

export function clearScreenshots() {
    for (const { url } of shots.values()) {
        URL.revokeObjectURL(url);
    }
    shots.clear();
    incoming.clear();
    $('screenshotsGrid').innerHTML = '';
}

export async function downloadZip(siteName, onProgress) {
    if (shots.size === 0) {
        throw new Error('No screenshots to download');
    }
    const zip = new JSZip();
    for (const [filename, { blob }] of shots) {
        zip.file(filename, blob);
    }
    const zipBlob = await zip.generateAsync(
        { type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 6 } },
        (metadata) => onProgress(Math.round(metadata.percent)),
    );
    saveAs(zipBlob, `${siteName}-screenshots.zip`);
}

export function openModal(url) {
    $('modalImage').src = url;
    $('imageModal').classList.add('active');
    document.body.classList.add('modal-open');
}

export function closeModal() {
    $('imageModal').classList.remove('active');
    document.body.classList.remove('modal-open');
}

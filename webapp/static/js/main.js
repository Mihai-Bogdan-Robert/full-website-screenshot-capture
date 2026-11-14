import { cancelCurrentJob, startCapture, startNewCapture } from './capture.js';
import { $ } from './dom.js';
import { initForm } from './form.js';
import { closeModal, downloadZip } from './screenshots.js';
import { initSocket } from './socket.js';

async function onDownload() {
    const button = $('downloadBtn');
    const original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner"></span> Generating ZIP...';

    try {
        await downloadZip(siteName(), (percent) => {
            button.innerHTML = `📦 Compressing... ${percent}%`;
        });
    } catch (error) {
        console.error('Error generating ZIP:', error);
        alert(error.message);
    } finally {
        button.disabled = false;
        button.innerHTML = original;
    }
}

function siteName() {
    const input = $('url').value.trim();
    try {
        return new URL(/^https?:\/\//.test(input) ? input : `https://${input}`).hostname.replace(/\./g, '-');
    } catch (error) {
        return 'screenshots';
    }
}

initForm();
initSocket();

$('captureForm').addEventListener('submit', (event) => {
    event.preventDefault();
    startCapture();
});
$('jobStatus').addEventListener('click', (event) => {
    if (event.target.closest('[data-action="cancel"]')) {
        cancelCurrentJob();
    }
});
$('downloadBtn').addEventListener('click', onDownload);
$('newCaptureBtn').addEventListener('click', startNewCapture);

$('modalClose').addEventListener('click', closeModal);
$('imageModal').addEventListener('click', (event) => {
    if (event.target === $('imageModal')) {
        closeModal();
    }
});
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeModal();
    }
});

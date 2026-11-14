// The progress card: message, counters, and the state of the buttons.
import { $, hide, show } from './dom.js';
import { screenshotCount } from './screenshots.js';

const RUNNING_INDICATOR = `
    <div class="indicator-running">
        <span class="spinner"></span>
        <span class="muted pulse">Processing...</span>
    </div>
    <button type="button" data-action="cancel" class="btn btn-danger">✕ Cancel</button>`;

const resultIndicator = (kind, icon, text) => `
    <div class="indicator-result result-${kind}">
        <span class="icon">${icon}</span>
        <span id="resultText">${text}</span>
    </div>`;

export function showJobStatus(job) {
    hide('mainCard');
    hide('captureForm');
    show('jobStatus');
    $('jobId').textContent = job.label || `Job ID: ${String(job.id).slice(0, 8)}`;
    updateJobStatus(job);
}

export function updateJobStatus(job) {
    $('statusMessage').textContent = job.message;
    updateCounters(job);

    const renderers = { completed: renderCompleted, cancelled: renderCancelled, failed: renderFailed };
    (renderers[job.status] || renderRunning)(job);
}

// The progress message is the only place the page learns the counts from.
function updateCounters(job) {
    const message = job.message || '';

    const crawling = message.match(/Crawling\s+pages.*?\((\d+)\/(\d+)\s+found\)/i);
    if (crawling) {
        setCrawlCounter(crawling[1], crawling[2]);
    }
    const crawled = message.match(/Crawled\s+(\d+)\s+pages/i);
    if (crawled) {
        setCrawlCounter(crawled[1], crawled[1]);
    }
    const inSitemap = message.match(/Found\s+(\d+)\s+pages\s+in\s+sitemap/i);
    if (inSitemap) {
        show('screenshotStatus');
        $('screenshotTotal').textContent = inSitemap[1];
    }
    const capturing = message.match(/Capturing\s+screenshot\s+(\d+)\/(\d+)/i);
    if (capturing) {
        show('screenshotStatus');
        $('screenshotCount2').textContent = capturing[1];
        $('screenshotTotal').textContent = capturing[2];
    }

    const received = screenshotCount();
    if (received > 0) {
        show('screenshotStatus');
        $('screenshotCount2').textContent = received;
    }
}

function setCrawlCounter(found, total) {
    show('crawlStatus');
    $('crawlCount').textContent = found;
    $('crawlTotal').textContent = total;
}

function renderCompleted(job) {
    hide('crawlStatus');
    const received = screenshotCount();
    if (job.result) {
        const total = job.result.screenshots || received;
        show('screenshotStatus');
        $('screenshotCount2').textContent = total;
        $('screenshotTotal').textContent = total;
    }
    $('statusIndicator').innerHTML = resultIndicator('ok', '✓', 'Completed successfully!');
    show('jobActions');
    if (received > 0) {
        show('screenshotsGallery');
    }
}

function renderCancelled() {
    $('statusIndicator').innerHTML = resultIndicator('cancelled', '⊘', 'Cancelled by user');
    show('newCaptureBtn');
    show('jobActions');
    if (screenshotCount() > 0) {
        show('downloadBtn');
        show('screenshotsGallery');
    } else {
        hide('downloadBtn');
    }
}

function renderFailed(job) {
    $('statusIndicator').innerHTML = resultIndicator('failed', '✗', '');
    // textContent: the error can contain text from a hostile website.
    $('resultText').textContent = job.error || 'Failed';
    show('newCaptureBtn');
    show('jobActions');
    hide('downloadBtn');
}

function renderRunning() {
    $('statusIndicator').innerHTML = RUNNING_INDICATOR;
}

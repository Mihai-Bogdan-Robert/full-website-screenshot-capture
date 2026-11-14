// The capture form: live summary, site preview, sitemap check.
import { checkSitemap } from './api.js';
import { $, hide, show } from './dom.js';

const MODE_LABELS = { sitemap: '🗺️ Sitemap', crawl: '🕷️ Crawl' };
const DEVICE_LABELS = {
    desktop: '🖥️ Desktop (1920×1080)',
    mobile: '📱 Mobile (390×844)',
    both: '📱🖥️ Both',
};
const MODE_DESCRIPTIONS = {
    sitemap: "Uses the website's sitemap.xml to find pages. Fast and reliable if available.",
    crawl: 'Crawls the website by following links from the homepage. Works for sites without sitemaps.',
};

const INPUT_DEBOUNCE_MS = 800;
const PREVIEW_TIMEOUT_MS = 8000;
const MIN_URL_LENGTH = 3;

const checked = (name) => document.querySelector(`input[name="${name}"]:checked`).value;

export function readForm() {
    return {
        url: $('url').value.trim(),
        maxPages: parseInt($('maxPages').value, 10),
        mode: checked('mode'),
        device: checked('device'),
    };
}

function updateSummary() {
    const url = $('url').value.trim();
    $('summaryUrl').textContent = url || 'Not set';
    $('summaryUrl').title = url;
    $('summaryMode').textContent = MODE_LABELS[checked('mode')];
    $('summaryDevice').textContent = DEVICE_LABELS[checked('device')];
    $('summaryMaxPages').textContent = $('maxPages').value;
}

function updateModeDescription() {
    $('modeDescription').textContent = MODE_DESCRIPTIONS[checked('mode')];
}

let previewTimer = null;

function loadPreview(url) {
    const address = /^https?:\/\//.test(url) ? url : `https://${url}`;
    show('previewSection');
    $('previewUrl').textContent = address;
    show('previewLoading');
    hide('previewError');

    const frame = $('previewFrame');
    frame.onload = () => {
        clearTimeout(previewTimer);
        hide('previewLoading');
    };
    frame.src = address;

    // A frame never reports that the site refused to be embedded, so give up after a while.
    clearTimeout(previewTimer);
    previewTimer = setTimeout(() => {
        if (!$('previewLoading').classList.contains('hidden')) {
            hide('previewLoading');
            show('previewError');
        }
    }, PREVIEW_TIMEOUT_MS);
}

async function updateSitemapAvailability(url) {
    const radio = $('sitemapRadio');
    const message = $('sitemapMessage');
    show('sitemapStatus');
    message.className = '';
    message.textContent = '⏳ Checking sitemap...';

    const exists = await checkSitemap(url);
    radio.disabled = !exists;
    message.className = exists ? 'hint-ok' : 'hint-error';
    message.textContent = exists ? '✓ Sitemap available' : '✗ No sitemap was found!';

    if (!exists && radio.checked) {
        document.querySelector('input[name="mode"][value="crawl"]').checked = true;
        updateModeDescription();
        updateSummary();
    }
}

export function initForm() {
    let inputTimer = null;
    $('url').addEventListener('input', (event) => {
        updateSummary();
        clearTimeout(inputTimer);
        inputTimer = setTimeout(() => {
            const url = event.target.value.trim();
            if (url.length > MIN_URL_LENGTH) {
                loadPreview(url);
                updateSitemapAvailability(url);
            } else {
                hide('previewSection');
                hide('sitemapStatus');
            }
        }, INPUT_DEBOUNCE_MS);
    });

    document.querySelectorAll('input[name="mode"]').forEach((radio) => {
        radio.addEventListener('change', () => {
            updateModeDescription();
            updateSummary();
        });
    });
    document.querySelectorAll('input[name="device"]').forEach((radio) => {
        radio.addEventListener('change', updateSummary);
    });
    $('maxPages').addEventListener('input', updateSummary);

    updateModeDescription();
    updateSummary();
}

export function resetSubmitButton() {
    $('submitBtn').disabled = false;
    $('submitBtn').textContent = 'Start Capturing';
}

export function setSubmitting() {
    $('submitBtn').disabled = true;
    $('submitBtn').innerHTML = '<span class="spinner"></span>';
}

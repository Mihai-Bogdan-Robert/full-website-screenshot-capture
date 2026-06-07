// Global state
let captureJob = null;
let currentJobId = null;
let pollInterval = null;

// DOM Elements
const formSection = document.getElementById('form-section');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');

const captureForm = document.getElementById('capture-form');
const submitBtn = document.getElementById('submit-btn');
const cancelBtn = document.getElementById('cancel-btn');

const domainInput = document.getElementById('domain');
const maxPagesInput = document.getElementById('max-pages');
const discoveryCheckboxes = document.querySelectorAll('input[name="discovery"]');
const deviceCheckboxes = document.querySelectorAll('input[name="device"]');

const progressMessage = document.getElementById('progress-message');
const progressFill = document.getElementById('progress-fill');
const progressPercent = document.getElementById('progress-percent');

const statUrlsFound = document.getElementById('stat-urls-found');
const statCaptured = document.getElementById('stat-captured');
const statFailed = document.getElementById('stat-failed');

const screenshotsContainer = document.getElementById('screenshots-container');
const failedUrlsSection = document.getElementById('failed-urls-section');
const failedUrlsList = document.getElementById('failed-urls-list');

const downloadAllBtn = document.getElementById('download-all-btn');
const newCaptureBtn = document.getElementById('new-capture-btn');

// Event Listeners
captureForm.addEventListener('submit', handleFormSubmit);
cancelBtn.addEventListener('click', handleCancel);
downloadAllBtn.addEventListener('click', handleDownloadAll);
newCaptureBtn.addEventListener('click', resetForm);

// Ensure at least one option is selected
discoveryCheckboxes.forEach(cb => {
    cb.addEventListener('change', ensureMinSelection('discovery'));
});

deviceCheckboxes.forEach(cb => {
    cb.addEventListener('change', ensureMinSelection('device'));
});

function ensureMinSelection(name) {
    return function() {
        const checked = document.querySelectorAll(`input[name="${name}"]:checked`);
        if (checked.length === 0) {
            event.target.checked = true;
        }
    };
}

/**
 * Handle form submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();

    const domain = domainInput.value.trim();
    const maxPages = parseInt(maxPagesInput.value) || 200;
    
    const discovery = Array.from(discoveryCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);
    
    const devices = Array.from(deviceCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

    if (!domain) {
        alert('Please enter a domain');
        return;
    }

    if (discovery.length === 0 || devices.length === 0) {
        alert('Please select at least one discovery method and device type');
        return;
    }

    // Disable form
    submitBtn.disabled = true;

    // Show progress section
    formSection.style.display = 'none';
    resultsSection.style.display = 'none';
    progressSection.style.display = 'block';

    // Reset progress
    updateProgress('Initializing capture...', 0);

    try {
        // Start capture job
        const response = await fetch('/api/capture/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                domain: domain,
                max_pages: maxPages,
                discovery_modes: discovery,
                devices: devices
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start capture job');
        }

        const data = await response.json();
        currentJobId = data.job_id;

        // Start polling for progress
        pollJobProgress();
        pollInterval = setInterval(pollJobProgress, 1000);

    } catch (error) {
        console.error('Error:', error);
        alert('Error: ' + error.message);
        submitBtn.disabled = false;
        progressSection.style.display = 'none';
        formSection.style.display = 'block';
    }
}

/**
 * Poll for job progress
 */
async function pollJobProgress() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`/api/capture/progress/${currentJobId}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch progress');
        }

        const data = await response.json();

        // Update progress bar
        updateProgress(data.message, data.progress);

        // Update stats
        statUrlsFound.textContent = data.urls_found || 0;
        statCaptured.textContent = data.screenshots || 0;
        statFailed.textContent = data.failed || 0;

        // Check if job is complete
        if (data.status === 'completed') {
            clearInterval(pollInterval);
            showResults(data);
        } else if (data.status === 'failed') {
            clearInterval(pollInterval);
            alert('Capture job failed: ' + (data.error || 'Unknown error'));
            submitBtn.disabled = false;
            progressSection.style.display = 'none';
            formSection.style.display = 'block';
        }

    } catch (error) {
        console.error('Error polling progress:', error);
    }
}

/**
 * Update progress display
 */
function updateProgress(message, percent) {
    progressMessage.textContent = message;
    progressFill.style.width = percent + '%';
    progressPercent.textContent = percent + '%';
}

/**
 * Handle cancel button
 */
async function handleCancel() {
    if (!currentJobId) return;

    if (!confirm('Are you sure you want to cancel this capture job?')) {
        return;
    }

    try {
        await fetch(`/api/capture/cancel/${currentJobId}`, {
            method: 'POST'
        });

        clearInterval(pollInterval);
        submitBtn.disabled = false;
        progressSection.style.display = 'none';
        formSection.style.display = 'block';

    } catch (error) {
        console.error('Error cancelling job:', error);
        alert('Error cancelling job: ' + error.message);
    }
}

/**
 * Show results
 */
function showResults(data) {
    clearInterval(pollInterval);

    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';

    // Update result stats
    document.getElementById('result-success').textContent = data.screenshots || 0;
    document.getElementById('result-failed').textContent = data.failed || 0;
    document.getElementById('result-total').textContent = data.urls_found || 0;

    // Show failed URLs if any
    if (data.failed_urls && data.failed_urls.length > 0) {
        failedUrlsSection.style.display = 'block';
        failedUrlsList.innerHTML = data.failed_urls
            .map(url => `<li>❌ ${escapeHtml(url)}</li>`)
            .join('');
    } else {
        failedUrlsSection.style.display = 'none';
    }

    // Display screenshots
    displayScreenshots(data.screenshots_data || []);

    submitBtn.disabled = false;
}

/**
 * Display screenshots in grid
 */
function displayScreenshots(screenshots) {
    screenshotsContainer.innerHTML = '';

    if (!screenshots || screenshots.length === 0) {
        screenshotsContainer.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #6b7280;">No screenshots to display</p>';
        return;
    }

    screenshots.forEach(screenshot => {
        const card = document.createElement('div');
        card.className = 'screenshot-card';

        const img = document.createElement('img');
        img.className = 'screenshot-image';
        img.src = 'data:image/png;base64,' + screenshot.data;
        img.alt = screenshot.filename;

        const info = document.createElement('div');
        info.className = 'screenshot-info';

        const name = document.createElement('div');
        name.className = 'screenshot-name';
        name.textContent = screenshot.filename;

        const downloadBtn = document.createElement('a');
        downloadBtn.className = 'screenshot-download';
        downloadBtn.href = 'data:image/png;base64,' + screenshot.data;
        downloadBtn.download = screenshot.filename;
        downloadBtn.textContent = '⬇️ Download';

        info.appendChild(name);
        info.appendChild(downloadBtn);

        card.appendChild(img);
        card.appendChild(info);

        screenshotsContainer.appendChild(card);
    });
}

/**
 * Handle download all screenshots
 */
function handleDownloadAll() {
    const screenshots = document.querySelectorAll('.screenshot-download');
    
    if (screenshots.length === 0) {
        alert('No screenshots to download');
        return;
    }

    // Trigger download for each screenshot
    screenshots.forEach((btn, index) => {
        setTimeout(() => {
            btn.click();
        }, index * 200);
    });

    alert(`Downloading ${screenshots.length} screenshot(s)...`);
}

/**
 * Reset form to initial state
 */
function resetForm() {
    currentJobId = null;
    clearInterval(pollInterval);

    captureForm.reset();
    screenshotsContainer.innerHTML = '';
    failedUrlsList.innerHTML = '';
    failedUrlsSection.style.display = 'none';

    formSection.style.display = 'block';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';

    submitBtn.disabled = false;

    // Reset checkboxes to defaults
    document.querySelector('input[name="discovery"][value="sitemap"]').checked = true;
    document.querySelector('input[name="device"][value="desktop"]').checked = true;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Initialize on page load
window.addEventListener('load', () => {
    // Set default domain focus
    domainInput.focus();
});

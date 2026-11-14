// Runs a capture from the form to the final state: one job per device, one after the other.
import { cancelJob, createJob, waitForJob } from './api.js';
import { readForm, resetSubmitButton, setSubmitting } from './form.js';
import { $, hide, show } from './dom.js';
import { clearScreenshots, screenshotCount } from './screenshots.js';
import { subscribe } from './socket.js';
import { resetState, state } from './state.js';
import { showJobStatus, updateJobStatus } from './status.js';

export async function startCapture() {
    const { url, maxPages, mode, device } = readForm();
    if (!url) {
        alert('Please enter a URL');
        return;
    }

    resetState();
    clearScreenshots();
    setSubmitting();

    const devices = device === 'both' ? ['desktop', 'mobile'] : [device];
    const jobs = [];

    try {
        for (const [index, deviceName] of devices.entries()) {
            const job = await createJob({ url, maxPages, mode, device: deviceName });
            state.jobIds.add(job.id);
            state.currentJobId = job.id;
            subscribe(job.id);

            const label = devices.length > 1 ? `Desktop + Mobile (${index + 1}/2)` : null;
            showJobStatus({ ...job, label });

            const finished = await waitForJob(job.id);
            jobs.push(finished);
            if (finished.status !== 'completed') {
                break;
            }
        }
    } catch (error) {
        if (jobs.length === 0 && state.jobIds.size === 0) {
            alert(error.message);
            resetCapture();
        } else {
            updateJobStatus({ status: 'failed', message: 'Capture failed', error: error.message });
        }
        return;
    }

    updateJobStatus(summarize(jobs, devices.length));
}

// One job is shown as it is. Two jobs become one combined result.
function summarize(jobs, expected) {
    const last = jobs[jobs.length - 1];
    if (expected === 1 || last.status !== 'completed' || jobs.length < expected) {
        return last;
    }
    return {
        ...last,
        message: 'All captures completed!',
        result: { screenshots: screenshotCount() },
    };
}

export async function cancelCurrentJob() {
    if (state.currentJobId) {
        await cancelJob(state.currentJobId);
    }
}

export function resetCapture() {
    resetSubmitButton();
    hide('jobActions');
    show('downloadBtn');
}

export function startNewCapture() {
    resetCapture();
    hide('jobStatus');
    hide('screenshotsGallery');
    clearScreenshots();
    show('mainCard');
    show('captureForm');
    resetState();
}

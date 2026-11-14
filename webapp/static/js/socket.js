// Live updates from the server: progress while a capture runs, and the screenshot chunks.
import { isTerminal } from './api.js';
import { receiveChunk } from './screenshots.js';
import { state } from './state.js';
import { updateJobStatus } from './status.js';

export const socket = io();

export function subscribe(jobId) {
    socket.emit('subscribe', { job_id: jobId });
}

export function initSocket() {
    // After a dropped connection the server no longer knows which job we were watching.
    socket.on('connect', () => {
        if (state.currentJobId) {
            subscribe(state.currentJobId);
        }
    });

    socket.on('job_update', (job) => {
        // The final state is shown by the capture flow, once every job of the capture is done.
        if (state.jobIds.has(job.id) && !isTerminal(job)) {
            updateJobStatus(job);
        }
    });

    socket.on('screenshot_chunk', (data) => {
        if (state.jobIds.has(data.job_id)) {
            receiveChunk(data);
        }
    });
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };
const TERMINAL_STATUSES = ['completed', 'failed', 'cancelled'];
const POLL_INTERVAL_MS = 1000;

export async function createJob({ url, maxPages, mode, device }) {
    let response;
    try {
        response = await fetch('/api/jobs', {
            method: 'POST',
            headers: JSON_HEADERS,
            body: JSON.stringify({ url, max_pages: maxPages, mode, device }),
        });
    } catch (error) {
        throw new Error('Failed to connect to server');
    }
    const body = await response.json();
    if (!response.ok) {
        throw new Error(body.error || 'Failed to start capture');
    }
    return body;
}

export async function cancelJob(jobId) {
    const response = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
    return response.ok;
}

export async function checkSitemap(url) {
    try {
        const response = await fetch('/api/check-sitemap', {
            method: 'POST',
            headers: JSON_HEADERS,
            body: JSON.stringify({ url }),
        });
        return (await response.json()).exists === true;
    } catch (error) {
        return false;
    }
}

// Poll until the job reaches a final status. Live progress arrives over the socket; this is
// what notices the end even if a socket message is missed.
export function waitForJob(jobId) {
    return new Promise((resolve) => {
        const poll = async () => {
            try {
                const response = await fetch(`/api/jobs/${jobId}`);
                const job = await response.json();
                if (TERMINAL_STATUSES.includes(job.status)) {
                    resolve(job);
                    return;
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
            setTimeout(poll, POLL_INTERVAL_MS);
        };
        poll();
    });
}

export const isTerminal = (job) => TERMINAL_STATUSES.includes(job.status);

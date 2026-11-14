// What the page is tracking right now. "Both" devices means two jobs, one after the other.
export const state = {
    jobIds: new Set(),      // every job of the capture in progress
    currentJobId: null,     // the job that is running now (what Cancel stops)
};

export function resetState() {
    state.jobIds.clear();
    state.currentJobId = null;
}

import {fetchJSON, validateProgress} from './api-client.js';

export class JobMonitor {
  constructor(onUpdate, onError) { this.onUpdate = onUpdate; this.onError = onError; this.generation = 0; this.active = false; }
  stop() { this.generation += 1; clearTimeout(this.timer); this.controller?.abort(); this.active = false; }
  start(jobId) {
    this.stop(); this.jobId = jobId; this.active = true;
    const generation = this.generation;
    const poll = async () => {
      this.controller = new AbortController();
      try {
        const {data} = await fetchJSON(`/api/v1/jobs/${jobId}`, {signal: this.controller.signal});
        if (generation !== this.generation) return;
        validateProgress(data, jobId);
        const terminal = ['COMPLETED', 'FAILED'].includes(data.status);
        if (terminal) this.active = false;
        this.onUpdate(data);
        if (!terminal) this.timer = setTimeout(poll, 1500);
      } catch (error) {
        if (generation !== this.generation) return;
        this.active = false; this.onError(error);
      }
    };
    poll();
  }
}

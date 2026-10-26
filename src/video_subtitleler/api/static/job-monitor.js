import {fetchJSON, validateProgress} from './api-client.js';

export class JobMonitor {
  constructor(onUpdate, onError, onWaiting = () => {}) { this.onUpdate = onUpdate; this.onError = onError; this.onWaiting = onWaiting; this.generation = 0; this.active = false; this.unfinished = false; }
  stop() { this.generation += 1; clearTimeout(this.timer); this.controller?.abort(); this.active = false; this.unfinished = false; }
  resume() { if (this.jobId && !this.active) this.start(this.jobId); }
  start(jobId) {
    this.stop(); this.jobId = jobId; this.active = true; this.unfinished = true; this.recovery = 0;
    const generation = this.generation;
    const poll = async () => {
      if (generation !== this.generation) return;
      this.controller = new AbortController();
      try {
        const {data} = await fetchJSON(`/api/v1/jobs/${jobId}`, {signal: this.controller.signal});
        if (generation !== this.generation) return;
        validateProgress(data, jobId);
        this.recovery = 0; this.onWaiting('');
        const terminal = ['COMPLETED', 'FAILED'].includes(data.status);
        if (terminal) { this.active = false; this.unfinished = false; }
        this.onUpdate(data);
        if (!terminal) this.timer = setTimeout(poll, 1500);
      } catch (error) {
        if (generation !== this.generation) return;
        if (error.transient && this.recovery < 3) {
          const wait = [1500, 3000, 6000][this.recovery++];
          this.onWaiting(`Conexão interrompida. Tentativa de reconexão ${this.recovery}/3…`);
          this.timer = setTimeout(poll, wait);
        } else {
          this.active = false;
          if (error.status === 404) this.unfinished = false;
          this.onWaiting(''); this.onError(error, error.status !== 404);
        }
      }
    };
    poll();
  }
}

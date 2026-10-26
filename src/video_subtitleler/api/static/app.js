import {bindForm} from './form.js';
import {submitVideo} from './api-client.js';
import {JobMonitor} from './job-monitor.js';

const $ = (selector) => document.querySelector(selector);
const form = bindForm();
let sending = false;

export async function connect() {
  const dot = $('#connection-dot'), text = $('#connection-text'), retry = $('#retry-config');
  retry.hidden = true; text.textContent = 'Conectando ao serviço…'; form.setConfig(null);
  try {
    const response = await fetch('/api/v1/ui-config', {signal: AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error('unavailable');
    const config = await response.json();
    if (!Number.isSafeInteger(config.max_upload_bytes) || config.max_upload_bytes <= 0) throw new Error('invalid');
    dot.className = 'status-dot online'; text.textContent = 'Serviço conectado'; form.setConfig(config);
  } catch { dot.className = 'status-dot offline'; text.textContent = 'Serviço indisponível'; retry.hidden = false; }
}

function view(name) {
  for (const key of ['form', 'progress', 'result']) $(`#${key}-view`).hidden = key !== name;
  document.querySelectorAll('.phase-strip > span').forEach((item, index) => item.classList.toggle('current', index === ['form', 'progress', 'result'].indexOf(name)));
}
function showJobError(message) { $('#job-error').textContent = message; $('#job-error').hidden = false; $('#new-from-error').hidden = false; }
const monitor = new JobMonitor((job) => {
  $('#progress-fill').style.width = `${job.progress_pct}%`; $('#progress-bar').setAttribute('aria-valuenow', job.progress_pct); $('#progress-percent').textContent = `${job.progress_pct}%`;
  $('#job-status').textContent = {QUEUED: 'Na fila', PROCESSING: 'Processando', COMPLETED: 'Concluído', FAILED: 'Falhou'}[job.status];
  $('#job-description').textContent = job.status === 'QUEUED' ? 'Seu vídeo está na fila.' : 'Você pode acompanhar o processamento nesta página.';
  if (job.status === 'FAILED') { showJobError(job.error || 'Não foi possível processar o vídeo. Confira o arquivo e tente novamente.'); form.setBusy(false); }
  if (job.status === 'COMPLETED') {
    $('#download-link').href = `/api/v1/jobs/${job.job_id}/download`; $('#download-link').download = `${job.job_id}.mp4`;
    form.setBusy(false); view('result'); $('#result-title').focus();
  }
}, (error) => showJobError(`O acompanhamento foi interrompido. ${error.message} O processamento pode continuar no servidor.`));

$('#upload-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (sending || monitor.active) return;
  form.showError();
  let body;
  try { body = form.payload(); } catch (error) { form.showError(error.message); return; }
  sending = true; form.setBusy(true); $('#submit-hint').textContent = 'Enviando vídeo…';
  try {
    const accepted = await submitVideo(body);
    $('#job-error').hidden = true; $('#new-from-error').hidden = true;
    view('progress'); $('#progress-title').focus(); monitor.start(accepted.job_id);
  } catch (error) { form.showError(`${error.message}${!error.status ? ' O envio não será repetido automaticamente; ele pode já ter sido aceito.' : ''}`); form.setBusy(false); }
  finally { sending = false; $('#submit-hint').textContent = 'Seu arquivo será processado neste serviço.'; }
});
function reset() { monitor.stop(); form.reset(); view('form'); $('#choose-file').focus(); }
$('#new-video').addEventListener('click', reset);
$('#new-from-error').addEventListener('click', reset);
$('#retry-config').addEventListener('click', connect);
window.addEventListener('beforeunload', (event) => { if (sending || monitor.active) { event.preventDefault(); event.returnValue = ''; } });
window.addEventListener('pagehide', () => monitor.stop());
await connect();

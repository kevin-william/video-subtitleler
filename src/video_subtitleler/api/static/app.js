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
function renderSteps(steps) {
  const labels = {PENDING: 'Aguardando', RUNNING: 'Em andamento', COMPLETED: 'Concluída', SKIPPED: 'Dispensada', FAILED: 'Falhou'};
  document.querySelectorAll('[data-step]').forEach((item, index) => {
    const state = steps[item.dataset.step] || 'PENDING';
    item.dataset.state = state; item.querySelector('[data-step-status]').textContent = labels[state];
    item.querySelector('.step-dot').textContent = {COMPLETED: '✓', SKIPPED: '−', FAILED: '!'}[state] || index + 1;
    if (state === 'RUNNING') item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current');
  });
}
const monitor = new JobMonitor((job) => {
  $('#progress-fill').style.width = `${job.progress_pct}%`; $('#progress-bar').setAttribute('aria-valuenow', job.progress_pct); $('#progress-percent').textContent = `${job.progress_pct}%`;
  $('#job-status').textContent = {QUEUED: 'Na fila', PROCESSING: 'Processando', COMPLETED: 'Concluído', FAILED: 'Falhou'}[job.status];
  renderSteps(job.steps);
  const currentLabel = job.current_step ? document.querySelector(`[data-step="${job.current_step}"] strong`).textContent : '';
  $('#job-description').textContent = job.status === 'QUEUED' ? 'Seu vídeo está na fila.' : currentLabel;
  $('#resume-job').hidden = true;
  if (job.status === 'FAILED') { showJobError(job.error || 'Não foi possível processar o vídeo. Confira o arquivo e tente novamente.'); form.setBusy(false); }
  if (job.status === 'COMPLETED') {
    $('#download-link').href = `/api/v1/jobs/${job.job_id}/download`; $('#download-link').download = `${job.job_id}.mp4`;
    form.setBusy(false); view('result'); $('#result-title').focus();
  }
}, (error, resumable) => {
  showJobError(error.status === 404 ? 'Processamento não encontrado. O servidor pode ter sido reiniciado ou o registro não está disponível.' : `O acompanhamento foi pausado. ${error.message} O processamento pode continuar no servidor.`);
  $('#job-status').textContent = 'Acompanhamento interrompido'; $('#resume-job').hidden = !resumable;
}, (message) => { $('#poll-notice').textContent = message; $('#poll-notice').hidden = !message; });

$('#upload-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (sending || monitor.active) return;
  form.showError();
  let body;
  try { body = form.payload(); } catch (error) { form.showError(error.message); return; }
  sending = true; form.setBusy(true); $('#submit-hint').textContent = 'Enviando vídeo…';
  try {
    const accepted = await submitVideo(body);
    $('#job-error').hidden = true; $('#new-from-error').hidden = true; $('#resume-job').hidden = true; $('#poll-notice').hidden = true;
    $('#progress-fill').style.width = '0%'; $('#progress-bar').setAttribute('aria-valuenow', 0); $('#progress-percent').textContent = '0%'; $('#job-status').textContent = 'Na fila'; renderSteps({});
    view('progress'); $('#progress-title').focus(); monitor.start(accepted.job_id);
  } catch (error) { form.showError(`${error.message}${!error.status ? ' O envio não será repetido automaticamente; ele pode já ter sido aceito.' : ''}`); form.setBusy(false); }
  finally { sending = false; $('#submit-hint').textContent = 'Seu arquivo será processado neste serviço.'; }
});
function reset() { monitor.stop(); form.reset(); view('form'); $('#choose-file').focus(); }
$('#new-video').addEventListener('click', reset);
$('#new-from-error').addEventListener('click', reset);
$('#resume-job').addEventListener('click', () => { $('#job-error').hidden = true; $('#resume-job').hidden = true; $('#new-from-error').hidden = true; $('#progress-title').focus(); monitor.resume(); });
$('#retry-config').addEventListener('click', connect);
window.addEventListener('beforeunload', (event) => { if (sending || monitor.unfinished) { event.preventDefault(); event.returnValue = ''; } });
window.addEventListener('pagehide', () => monitor.stop());
await connect();

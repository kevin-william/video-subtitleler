export class ServiceError extends Error {
  constructor(message, status = 0, transient = false) { super(message); this.status = status; this.transient = transient; }
}

export async function fetchJSON(url, options = {}, timeout = 10000) {
  const deadline = new AbortController();
  const timer = setTimeout(() => deadline.abort(), timeout);
  try {
    let response;
    try {
      const signal = options.signal ? AbortSignal.any([options.signal, deadline.signal]) : deadline.signal;
      response = await fetch(url, {...options, signal});
    } catch (error) {
      if (options.signal?.aborted) throw error;
      throw new ServiceError(deadline.signal.aborted ? 'O serviço demorou para responder.' : 'Não foi possível acessar o serviço. Confira a conexão.', 0, true);
    }
    let data;
    try { data = await response.json(); } catch {
      if (deadline.signal.aborted) throw new ServiceError('O serviço demorou para responder.', 0, true);
      throw new ServiceError('O serviço devolveu uma resposta inesperada.', response.status, response.status >= 500);
    }
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new ServiceError('O serviço devolveu uma resposta inesperada.', response.status);
    if (!response.ok) {
      let detail = typeof data.detail === 'string' ? data.detail : '';
      if (Array.isArray(data.detail)) detail = data.detail.map((entry) => typeof entry?.msg === 'string' ? entry.msg : '').filter(Boolean).join('; ');
      if (response.status === 413) detail = 'Os arquivos ultrapassam o limite de envio do serviço.';
      throw new ServiceError(detail || 'Não foi possível concluir a solicitação.', response.status, response.status >= 500);
    }
    return {data, status: response.status};
  } finally { clearTimeout(timer); }
}

export function validJobId(id) { return typeof id === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id); }

export async function submitVideo(body) {
  const {data, status} = await fetchJSON('/api/v1/subtitles/generate', {method: 'POST', body}, 120000);
  if (status !== 202 || !validJobId(data.job_id)) throw new ServiceError('O serviço não confirmou um processamento válido.');
  return data;
}

export function validateProgress(data, jobId) {
  const steps = ['extract_audio', 'transcription', 'llm_enhancement', 'generate_ass', 'burning_subtitles'];
  const states = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED'];
  if (data.job_id !== jobId || !['QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'].includes(data.status) || !Number.isInteger(data.progress_pct) || data.progress_pct < 0 || data.progress_pct > 100 || typeof data.steps !== 'object' || data.steps === null || !steps.every((key) => states.includes(data.steps[key])) || (data.current_step !== null && !steps.includes(data.current_step)) || (data.status === 'COMPLETED' && data.progress_pct !== 100) || (data.error != null && typeof data.error !== 'string')) throw new ServiceError('O serviço devolveu um progresso inválido.');
  return data;
}

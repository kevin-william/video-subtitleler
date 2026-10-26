export class ServiceError extends Error {
  constructor(message, status = 0, transient = false) { super(message); this.status = status; this.transient = transient; }
}

export async function fetchJSON(url, options = {}, timeout = 10000) {
  let response;
  try {
    const signal = options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(timeout)]) : AbortSignal.timeout(timeout);
    response = await fetch(url, {...options, signal});
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ServiceError('Não foi possível acessar o serviço. Confira a conexão.', 0, true);
  }
  let data;
  try { data = await response.json(); } catch { throw new ServiceError('O serviço devolveu uma resposta inesperada.', response.status, response.status >= 500); }
  if (!response.ok) {
    let detail = typeof data.detail === 'string' ? data.detail : '';
    if (Array.isArray(data.detail)) detail = data.detail.map((entry) => entry.msg || '').filter(Boolean).join('; ');
    if (response.status === 413) detail = 'Os arquivos ultrapassam o limite de envio do serviço.';
    throw new ServiceError(detail || 'Não foi possível concluir a solicitação.', response.status, response.status >= 500);
  }
  return {data, status: response.status};
}

export function validJobId(id) { return typeof id === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id); }

export async function submitVideo(body) {
  const {data, status} = await fetchJSON('/api/v1/subtitles/generate', {method: 'POST', body}, 120000);
  if (status !== 202 || !validJobId(data.job_id)) throw new ServiceError('O serviço não confirmou um processamento válido.');
  return data;
}

export function validateProgress(data, jobId) {
  if (data.job_id !== jobId || !['QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'].includes(data.status) || !Number.isInteger(data.progress_pct) || data.progress_pct < 0 || data.progress_pct > 100 || typeof data.steps !== 'object' || data.steps === null) throw new ServiceError('O serviço devolveu um progresso inválido.');
  return data;
}

export async function connect() {
  const dot = document.querySelector('#connection-dot');
  const text = document.querySelector('#connection-text');
  const retry = document.querySelector('#retry-config');
  retry.hidden = true;
  text.textContent = 'Conectando ao serviço…';
  try {
    const response = await fetch('/api/v1/ui-config', {signal: AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error('unavailable');
    const config = await response.json();
    if (!Number.isSafeInteger(config.max_upload_bytes) || config.max_upload_bytes <= 0) throw new Error('invalid');
    dot.className = 'status-dot online';
    text.textContent = 'Serviço conectado';
    return config;
  } catch {
    dot.className = 'status-dot offline';
    text.textContent = 'Serviço indisponível';
    retry.hidden = false;
    return null;
  }
}
document.querySelector('#retry-config').addEventListener('click', connect);
await connect();

const $ = (selector) => document.querySelector(selector);

export function fileSize(bytes) {
  return `${new Intl.NumberFormat('pt-BR', {maximumFractionDigits: 1}).format(bytes / 1000000)} MB`;
}

export function bindForm() {
  let file = null, busy = false, config = null;
  const error = $('#form-error');
  function showError(message = '') { error.textContent = message; error.hidden = !message; }
  function validateFiles(required = false) {
    if (!file) { if (required) throw new Error('Escolha um vídeo MP4 para começar.'); return; }
    if (!/\.mp4$/i.test(file.name)) throw new Error('O vídeo precisa estar no formato MP4.');
    if (file.size === 0) throw new Error('O arquivo de vídeo está vazio.');
    const external = $('#mode').value === 'external';
    const subtitle = external ? $('#external-file').files[0] : null;
    if (external && !subtitle && required) throw new Error('Escolha o arquivo de legenda externa.');
    if (subtitle) {
      if (subtitle.size === 0) throw new Error('O arquivo de legenda está vazio.');
      if (!/\.(srt|vtt|json)$/i.test(subtitle.name)) throw new Error('A legenda precisa ser SRT, VTT ou JSON.');
      if ($('input[name="style_preset"]:checked').value === 'instagram_music' && !/\.json$/i.test(subtitle.name)) throw new Error('O karaokê precisa de JSON com palavras alinhadas. SRT e VTT podem ser usados no estilo Cinema.');
    }
    if (config && file.size + (subtitle?.size || 0) > config.max_upload_bytes) throw new Error(`O limite de envio é ${fileSize(config.max_upload_bytes)}, somando vídeo e legenda.`);
  }
  function checkFiles() { try { validateFiles(); showError(); } catch (error) { showError(error.message); } }
  function setFile(value) {
    if (busy) return;
    file = value; $('#file-info').hidden = !file; $('#dropzone').hidden = Boolean(file);
    $('#file-name').textContent = file?.name || ''; $('#file-size').textContent = file ? fileSize(file.size) : ''; checkFiles();
  }
  function updateButton() { $('#submit-button').disabled = busy || !config; }
  $('#choose-file').addEventListener('click', () => $('#video-file').click());
  $('#video-file').addEventListener('change', (event) => setFile(event.target.files[0] || null));
  $('#remove-file').addEventListener('click', () => { setFile(null); $('#video-file').value = ''; $('#choose-file').focus(); });
  const zone = $('#dropzone');
  zone.addEventListener('dragover', (event) => { event.preventDefault(); if (!busy) zone.classList.add('dragging'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
  zone.addEventListener('drop', (event) => {
    event.preventDefault(); zone.classList.remove('dragging');
    if (event.dataTransfer.files.length !== 1) { showError('Escolha um vídeo de cada vez.'); return; }
    setFile(event.dataTransfer.files[0]);
  });
  $('#language').addEventListener('change', () => { $('#custom-language-label').hidden = $('#language').value !== 'custom'; });
  function externalOptions() {
    const external = $('#mode').value === 'external';
    $('#external-panel').hidden = !external;
    if (!external) $('#external-file').value = '';
    const karaoke = $('input[name="style_preset"]:checked').value === 'instagram_music';
    $('#external-file').accept = karaoke ? '.json' : '.srt,.vtt,.json';
    $('#external-hint').textContent = karaoke ? 'O karaokê exige JSON com palavras alinhadas. O serviço verificará o conteúdo.' : 'Use SRT, VTT ou JSON. O limite considera vídeo e legenda juntos.';
    checkFiles();
  }
  $('#mode').addEventListener('change', externalOptions);
  document.querySelectorAll('input[name="style_preset"]').forEach((input) => input.addEventListener('change', externalOptions));
  $('#external-file').addEventListener('change', checkFiles);
  return {
    showError,
    setConfig(value) { config = value; $('#upload-limit').textContent = value ? `MP4 · até ${fileSize(value.max_upload_bytes)}` : 'Reconecte ao serviço para enviar.'; checkFiles(); updateButton(); },
    setBusy(value) { busy = value; $('#form-fields').disabled = value; updateButton(); },
    reset() { busy = false; $('#upload-form').reset(); setFile(null); externalOptions(); $('#custom-language-label').hidden = true; $('#form-fields').disabled = false; showError(); updateButton(); },
    payload() {
      if (!config) throw new Error('Conecte ao serviço antes de enviar.');
      validateFiles(true);
      const language = $('#language').value === 'custom' ? $('#custom-language').value.trim() : $('#language').value;
      if (!/^(auto|[a-z]{2,3})$/.test(language)) throw new Error('Use um código de idioma com 2 ou 3 letras minúsculas.');
      const data = new FormData();
      data.append('video_file', file); data.append('transcription_mode', $('#mode').value);
      data.append('style_preset', $('input[name="style_preset"]:checked').value); data.append('language', language); data.append('custom_style', '{}');
      if ($('#mode').value === 'external') data.append('external_subtitle_file', $('#external-file').files[0]);
      return data;
    },
  };
}

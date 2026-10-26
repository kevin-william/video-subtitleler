const $ = (selector) => document.querySelector(selector);

export function fileSize(bytes) {
  return `${new Intl.NumberFormat('pt-BR', {maximumFractionDigits: 1}).format(bytes / 1000000)} MB`;
}

function bindStyleControls() {
  const fields = [...document.querySelectorAll('[data-style]')];
  const numeric = {font_size: [8, 200, true], inactive_opacity: [0, 1, false], margin_vertical: [0, 4096, true], cpl: [37, 42, true]};
  for (const field of fields) {
    field.addEventListener('input', () => {
      const key = field.dataset.style;
      const range = document.querySelector(`[data-range="${key}"]`);
      if (range && field.value !== '' && Number.isFinite(Number(field.value))) range.value = field.value;
      if (key.endsWith('_color') && /^#[a-f0-9]{6}$/i.test(field.value)) document.querySelector(key === 'active_color' ? '#picker-active' : '#picker-inactive').value = field.value;
    });
  }
  document.querySelectorAll('[data-range]').forEach((range) => range.addEventListener('input', () => {
    document.querySelector(`[data-style="${range.dataset.range}"]`).value = range.value;
  }));
  for (const [picker, key] of [['#picker-active', 'active_color'], ['#picker-inactive', 'inactive_color']]) {
    $(picker).addEventListener('input', () => { document.querySelector(`[data-style="${key}"]`).value = $(picker).value.toUpperCase(); });
  }
  function reset() {
    fields.forEach((input) => { input.value = ''; });
    document.querySelectorAll('[data-range]').forEach((range) => { range.value = range.defaultValue; });
    document.querySelector('input[name="alignment"][value=""]').checked = true;
    updateDefaults(); $('#picker-inactive').value = '#ffffff';
  }
  function updateDefaults() {
    if (!document.querySelector('[data-style="active_color"]').value) $('#picker-active').value = $('input[name="style_preset"]:checked').value === 'instagram_music' ? '#00ffcc' : '#ffffff';
  }
  updateDefaults();
  $('#reset-style').addEventListener('click', reset);
  return {
    reset,
    updateDefaults,
    values() {
      const result = {};
      for (const field of fields) {
        const key = field.dataset.style, value = field.value.trim();
        if (field.validity.badInput) throw new Error('Confira os números do estilo personalizado.');
        if (value === '') continue;
        if (key in numeric) {
          const [min, max, integer] = numeric[key], number = Number(value);
          if (!Number.isFinite(number) || number < min || number > max || (integer && !Number.isInteger(number))) throw new Error(`O ajuste ${field.closest('label').childNodes[0].textContent.trim().toLowerCase()} deve ser ${integer ? 'um inteiro ' : 'um número '}entre ${min} e ${max}.`);
          result[key] = number;
        } else if (key.endsWith('_color')) {
          if (!/^#[a-f0-9]{6}$/i.test(value)) throw new Error('Use uma cor no formato #RRGGBB.');
          result[key] = value.toUpperCase();
        } else {
          if (value.length > 100 || /[,{}\\\x00-\x1f]/.test(value)) throw new Error('O nome da fonte contém caracteres não permitidos.');
          result[key] = value;
        }
      }
      const alignment = $('input[name="alignment"]:checked').value;
      if (alignment) result.alignment = Number(alignment);
      return result;
    },
  };
}

export function bindForm() {
  const style = bindStyleControls();
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
    style.updateDefaults();
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
    reset() { busy = false; $('#upload-form').reset(); style.reset(); $('#advanced-style').open = false; setFile(null); externalOptions(); $('#custom-language-label').hidden = true; $('#form-fields').disabled = false; showError(); updateButton(); },
    payload() {
      if (!config) throw new Error('Conecte ao serviço antes de enviar.');
      validateFiles(true);
      const language = $('#language').value === 'custom' ? $('#custom-language').value.trim() : $('#language').value;
      if (!/^(auto|[a-z]{2,3})$/.test(language)) throw new Error('Use um código de idioma com 2 ou 3 letras minúsculas.');
      const data = new FormData();
      data.append('video_file', file); data.append('transcription_mode', $('#mode').value);
      data.append('style_preset', $('input[name="style_preset"]:checked').value); data.append('language', language); data.append('custom_style', JSON.stringify(style.values()));
      if ($('#mode').value === 'external') data.append('external_subtitle_file', $('#external-file').files[0]);
      return data;
    },
  };
}

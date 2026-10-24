# Video Subtitleler

Serviço Python para transcrever e gravar legendas em MP4, com presets cinema/séries e Instagram/música. O [índice de tarefas](tasks/index.md) registra o progresso e as dependências de cada entrega. Veja o [plano](IMPLEMENTATION_PLAN.md) para o escopo original.

## Instalação

Python 3.12. Em PowerShell, na raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev,api,cli,whisper,llm]"
```

Para reproduzir as versões testadas, instalar primeiro `pip install -r requirements-dev.lock`. O arquivo contém versões do ambiente Windows; FFmpeg e pesos não são pacotes pip. Os extras `api`, `cli`, `whisper` e `llm` podem ser instalados separadamente. A biblioteca básica requer apenas Pydantic e Pydantic Settings. As interfaces ficam disponíveis após as respectivas tarefas no índice.

## Configuração e contratos

Copie `.env.example` para `.env`. `Settings` usa argumentos explícitos > ambiente `SUBTITLE_*` > `.env` > padrões. `_env_file=None` desabilita o arquivo. Caminhos relativos partem do diretório atual. Importar o pacote ou carregar configurações não cria pastas, carrega modelos ou inicia subprocessos.

`Word(text, start, end)` usa segundos finitos e não negativos, com fim maior que início. `Segment` acrescenta `words` opcionais e `SubtitleTrack` contém idioma e segmentos. Tempos devem estar ordenados, sem sobreposição; palavras ficam dentro do segmento. Intervalos adjacentes são aceitos. Modelos congelados e tuplas protegem as trilhas de mutação. Diálogos sobrepostos são rejeitados pelo contrato inicial, sem correção silenciosa.

`SubtitleRequest` valida extensão MP4, modo, preset, idioma `auto` ou código minúsculo de 2–3 letras e overrides. `external` exige legenda SRT/VTT/JSON; os outros modos rejeitam esse argumento. Os serviços verificam existência e conteúdo dos arquivos. Padrões: Whisper direto e cinema.

`CustomStyle`: `active_color`/`inactive_color` em `#RRGGBB`, `font_name` sem controles ASS, `font_size` 8–200, `alignment` ASS 1–9, `margin_vertical` 0–4096, `inactive_opacity` 0–1 e `cpl` 37–42 (padrão 40). As escolhas que complementam o plano estão descritas no índice.

A chave LLM é SecretStr e fica fora do repr e da serialização de Settings. Não imprima seu valor explícito. `.env`, diretórios de trabalho, modelos e vídeos gerados estão no `.gitignore`.

## Testes

```powershell
New-Item -ItemType Directory -Path .tmp -Force | Out-Null
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
.\.venv\Scripts\python -m pytest -q
python scripts/verify_plan_excerpts.py tasks
```

As variáveis temporárias valem apenas para o processo atual e evitam falhas de permissão do ambiente de execução. No Windows, asyncio/TestClient precisam de comunicação local habilitada; bloqueá-la pode paralisar a inicialização do event loop. Os testes não acessam provedores externos nem baixam pesos. A suíte padrão registra skip no teste Whisper real se os recursos locais não forem informados.

## Extração de áudio

Instale FFmpeg e FFprobe com libass; configure `SUBTITLE_FFMPEG_PATH` e `SUBTITLE_FFPROBE_PATH` com nomes no PATH ou caminhos absolutos. FFprobe valida contêiner, duração, resolução de exibição (incluindo rotação) e áudio. A extração produz WAV PCM mono de 16 kHz. Vídeos sem áudio podem receber legendas externas, mas não podem ser transcritos. Timeout de mídia: `SUBTITLE_MEDIA_TIMEOUT`, padrão 600 s. Entrada e arquivos já existentes não são sobrescritos.

## Legendas externas

SRT e WebVTT UTF-8 (BOM aceito) preservam tempos e texto em múltiplas linhas; tags de marcação são convertidas para texto simples. O leitor implementa cues textuais, identificadores e comentários; ignora STYLE, REGION e configurações de posição WebVTT. Não implementa posicionamento ou formatação desses formatos. Tempos inválidos, sobreposição e conteúdo vazio são rejeitados.

JSON segue `SubtitleTrack`, incluindo palavras opcionais:

```json
{"language":"pt","segments":[{"text":"Olá mundo","start":0.1,"end":1.6,"words":[{"text":"Olá","start":0.1,"end":0.7},{"text":"mundo","start":0.9,"end":1.6}]}]}
```

Karaokê externo exige palavras realmente alinhadas, normalmente em JSON. SRT/VTT sem alinhamento atendem cinema. Não se fabricam tempos por palavra.

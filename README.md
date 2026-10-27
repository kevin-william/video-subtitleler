# Video Subtitleler

Serviço Python para transcrever e gravar legendas em MP4, com presets cinema/séries e Instagram/música. O [índice de tarefas](tasks/index.md) registra o progresso e as dependências de cada entrega. Veja o [plano](IMPLEMENTATION_PLAN.md) para o escopo original.

## Interface web

Inicie a aplicação e abra `http://127.0.0.1:8000/`:

```powershell
.\.venv\Scripts\python -m uvicorn video_subtitleler.api.app:app --host 127.0.0.1 --port 8000
```

1. Escolha ou arraste um vídeo MP4. O limite exibido vem da configuração do serviço e considera vídeo e legenda juntos.
2. Escolha Cinema ou Instagram, o idioma e o processamento. Use “Whisper + refinamento LLM” para o MiniMax configurado no servidor; “Legenda externa” exige SRT/VTT/JSON, e Instagram exige JSON com palavras alinhadas.
3. Se quiser, abra “Personalizar estilo”. Campos automáticos preservam os padrões do preset; “Restaurar estilo padrão” remove as personalizações.
4. Clique em “Gerar legendas” e acompanhe as cinco etapas. Consultas interrompidas tentam reconectar; “Retomar acompanhamento” consulta o mesmo job, sem reenviar o vídeo.
5. Assista ao resultado, baixe o MP4 ou escolha “Processar novo vídeo”. Se o refinamento não puder ser aplicado, o resultado informa que usou a transcrição original do Whisper.

Mantenha a página aberta durante o processamento: recarregá-la não recupera o acompanhamento e voltar ao envio não cancela o trabalho no servidor. Falhas de codec do navegador não impedem o download. Chaves e configuração de GPU/LLM ficam somente no servidor.

A interface usa assets locais, sem Node ou CDN obrigatório; `/docs` continua sendo documentação técnica. Para os testes, instale `.[dev,api,web-test]`, execute `python -m playwright install chromium` e `python -m pytest tests/web --browser chromium -q`. O Edge instalado pode ser usado com `--browser-channel msedge`. Versões em `requirements-web-test.lock`; evidências em [docs/web-interface/validation.md](docs/web-interface/validation.md).

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

## Transcrição Whisper

O modelo é carregado sob demanda com `word_timestamps=True`. Padrões: `small`, `cpu`, `int8`; configure `SUBTITLE_WHISPER_MODEL`, `SUBTITLE_WHISPER_DEVICE` e `SUBTITLE_WHISPER_COMPUTE_TYPE`. Um nome de modelo permite download pelo Faster-Whisper na primeira execução; um diretório de pesos local permite operação offline. A suíte usa somente pesos locais informados explicitamente.

O extra Whisper limita PyAV a `>=11,<17`: PyAV 19 removeu o argumento `metadata_errors` usado pelo Faster-Whisper 1.2.1. A combinação validada usa PyAV 16.1.0, registrada no lock. Resultado vazio ou alinhamento inválido gera erro claro; não altera tempos para forçar aprovação.

### GPU NVIDIA no Windows

Instale as bibliotecas CUDA 12/cuDNN 9 no ambiente do projeto:

```powershell
.\.venv\Scripts\python -m pip install -e ".[whisper,cuda]"
```

As versões NVIDIA validadas estão em `requirements-cuda.lock` (opcional: `pip install -r requirements-cuda.lock`). Requisitos upstream: [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper#gpu).

No `.env`, use:

```dotenv
SUBTITLE_WHISPER_MODEL=small
SUBTITLE_WHISPER_DEVICE=cuda
SUBTITLE_WHISPER_COMPUTE_TYPE=float16
```

Reinicie a aplicação após alterar a configuração. O adaptador registra as pastas de DLLs dos pacotes NVIDIA do ambiente Python atual ao carregar o Whisper em `cuda`/`auto`, sem alterar o PATH global. Ter driver com suporte a CUDA ou PyTorch com CUDA 13 em outro ambiente não fornece as DLLs CUDA 12 exigidas pelo Faster-Whisper. Os padrões gerais continuam `cpu`/`int8`; `.env.example` é portátil. Para reduzir o consumo de VRAM, pode-se usar `int8_float16`.

Teste real com voz autorizada e modelo já baixado:

```powershell
$env:SUBTITLE_TEST_MODEL = 'C:\caminho\para\pesos-locais'
$env:SUBTITLE_TEST_VOICE = 'C:\caminho\para\voz-em-ingles.wav'
.\.venv\Scripts\python -m pytest -m integration_whisper -q
```

O teste usa voz em inglês de pelo menos cinco palavras. A validação de entrega utilizou voz sintética local (Microsoft Zira) e Whisper tiny em CPU.

Para executar esse teste na GPU, defina também `SUBTITLE_TEST_DEVICE=cuda` e `SUBTITLE_TEST_COMPUTE_TYPE=float16`; use `SUBTITLE_TEST_MODEL` para indicar o diretório local do modelo a validar.

## Refinamento LLM e fallback

Configure `SUBTITLE_LLM_API_KEY`, `SUBTITLE_LLM_BASE_URL`, `SUBTITLE_LLM_MODEL` e `SUBTITLE_LLM_TIMEOUT` (30 s). Não há endpoint padrão apresentado como verificado. O cliente LangChain ChatOpenAI usa JSON mode, chave/endpoint/modelo configuráveis e zero retries. O timeout limita a chamada assíncrona; falhas, quota, indisponibilidade, JSON inválido ou quebra de identidade de palavras retornam a mesma trilha Whisper.

O modelo recebe ids e tempos, mas devolve somente ids/texto agrupado; os tempos são copiados localmente do original. Respostas com tempos extras, palavras ausentes, ids duplicados/fora de ordem ou expansão de uma palavra em várias são rejeitadas. Grupos LLM do Instagram têm 2–4 palavras, com sobra final menor.

O teste do SDK real usa um servidor OpenAI-compatible local. OpenCode Go foi validado adicionalmente com chamadas reais ao MiniMax M3.1 Flash nos dois presets, usando legenda sintética. Sem configuração LLM, o modo híbrido continua com Whisper e marca a etapa LLM como SKIPPED. Logs de fallback não incluem exceções que possam revelar chaves.

Configuração OpenCode Go (chave somente no `.env`, ignorado pelo Git):

```dotenv
SUBTITLE_LLM_API_KEY=sua-chave-local
SUBTITLE_LLM_BASE_URL=https://opencode.ai/inference/go/openai/v1
SUBTITLE_LLM_MODEL=minimax-m3.1-flash
SUBTITLE_LLM_TIMEOUT=30
```

MiniMax M3.1 Flash é a opção MiniMax de menor preço na [tabela Go consultada em 24/10/2026](https://opencode.ai/docs/go/); o consumo conta para a franquia da assinatura. A documentação direciona Go a agentes de programação; a aceitação das chamadas de validação não garante suporte contínuo a aplicações de legendagem. O cliente identifica-se como `video-subtitleler/0.1.0` e envia `x-opencode-session` por refinamento, sem imitar outro aplicativo. Para usar o refinamento, selecione o modo `llm_hybrid`; o modo `whisper_only` não chama a LLM. A qualidade das correções varia; a validação preserva identidade, quantidade e tempos das palavras e recorre ao original em caso de falha.

## Cinema e séries

`movie_series`: texto branco, Arial configurável, contorno preto 2 px, sombra leve, alinhamento inferior central e no máximo duas linhas por evento. CPL padrão 40, configurável de 37 a 42. Com palavras, a divisão usa seus limites reais; com segmentos externos, blocos longos dividem o intervalo proporcionalmente ao texto, sem alegar sincronismo por palavra. Palavras maiores que CPL são quebradas para caber.

ASS usa centésimos e cores BGR. Intervalos que colapsam para duração zero nessa precisão são rejeitados. Barras invertidas e chaves de texto recebido são representadas por glifos de largura cheia para impedir interpretação como comandos ASS. Verifique a disponibilidade da fonte escolhida; a resolução ASS acompanha o vídeo.

## Instagram e música

`instagram_music`: Impact configurável, centro da tela, blocos de 2–5 palavras (sobra final menor), palavras inativas brancas com 85% de opacidade e palavra ativa ciano `#00FFCC` por padrão. O gerador usa eventos ASS por intervalo com overrides de cor/opacidade, em vez de tags de karaokê acumulativas: o destaque anterior desaparece e pausas não têm palavra ativa. Todas as palavras do bloco permanecem visíveis. Linhas são divididas por uma estimativa de largura para acomodar vídeos estreitos.

Overrides são compartilhados pela API/CLI. Não se oferece alinhamento forçado de SRT/VTT. A suíte verifica o movimento e a ausência do destaque durante pausa também nos pixels do vídeo renderizado.

## Renderização

FFmpeg com filtro `ass`/libass codifica H.264 e áudio AAC em MP4, preservando duração, dimensões de exibição e presença de áudio. O modo padrão usa CPU (`libx264`); `SUBTITLE_RENDER_ENCODER` aceita opcionalmente `h264_nvenc`, `h264_qsv` ou `h264_amf`, com verificação de disponibilidade e erro explícito se falhar. O filtro ASS pode permanecer em CPU. Hardware não foi validado nesta entrega.

O render usa diretório temporário próprio, nome de ASS controlado, argumentos sem shell e saída publicada somente após FFprobe validar o resultado. Isso evita interpolar caminhos Windows com espaços/apóstrofos na sintaxe do filtro. Falhas removem somente parciais próprios. O destino precisa ser novo.

## Jobs e persistência

SQLite é padrão em `SUBTITLE_DATABASE_PATH` (`work/jobs.sqlite3`); memória serve a testes. UUID e criação UTC com timezone identificam cada job. Transições: QUEUED → PROCESSING → COMPLETED/FAILED, com atualização transacional e progresso monotônico. Somente conclusão com saída pode atingir 100%.

Etapas: extract_audio, transcription, llm_enhancement, generate_ass, burning_subtitles; estados PENDING/RUNNING/COMPLETED/FAILED/SKIPPED. Modelos públicos omitem caminhos internos. Persistência não implica retomada após reinício; jobs interrompidos podem permanecer no estado anterior. Sem fila distribuída ou coordenação entre múltiplos workers.

## Pipeline e amostras

O pipeline compartilhado isola temporários por job, preserva entrada e mantém saída final. `external` dispensa extração/Whisper/LLM; `whisper_only` extrai/transcreve; `llm_hybrid` acrescenta refinamento com fallback. Falhas reais de mídia/transcrição tornam o job FAILED. Caminhos de saída padrão usam UUID e não colidem entre jobs.

Para reproduzir amostras com voz e pesos locais:

```powershell
.\.venv\Scripts\python scripts/smoke_demo.py --voice voz.wav --model caminho-dos-pesos --output output/demo
```

O script cria pasta nova com entrada, JSON transcrito, ASS, vídeos dos dois presets, vídeo híbrido com fallback e evidências JSON. Não baixa modelos. Os arquivos gerados ficam fora do Git.

## CLI

```powershell
.\.venv\Scripts\python -m video_subtitleler.cli --help
.\.venv\Scripts\python -m video_subtitleler.cli process video.mp4 --style movie_series --output cinema.mp4
.\.venv\Scripts\python -m video_subtitleler.cli process video.mp4 --style instagram_music --language pt --output reels.mp4
.\.venv\Scripts\python -m video_subtitleler.cli process video.mp4 --transcription-mode external --external-subtitle legenda.srt --output legendado.mp4
.\.venv\Scripts\python -m video_subtitleler.cli process video.mp4 --transcription-mode llm_hybrid --style instagram_music --custom-style '{"active_color":"#FFD700","font_size":72}' --output karaoke.mp4
```

Após instalar o extra CLI, o comando `video-subtitleler` equivale ao módulo. A ajuda não carrega modelos ou executáveis. `whisper_only` é o padrão. Códigos de saída: 0 sucesso, 2 entrada inválida, 1 falha de processamento. Estilos existentes ou destinos existentes não são sobrescritos silenciosamente.

## API REST

```powershell
.\.venv\Scripts\python -m uvicorn video_subtitleler.api.app:app --host 127.0.0.1 --port 8000
```

Interface web em `http://127.0.0.1:8000/`; documentação técnica Swagger em `http://127.0.0.1:8000/docs`. Rotas:

| Método / rota | Resultado |
|---|---|
| POST `/api/v1/subtitles/generate` | Multipart; 202 com job_id, status QUEUED e created_at UTC |
| GET `/api/v1/jobs/{job_id}` | Estado, progresso, etapa atual, etapas e erro |
| GET `/api/v1/jobs/{job_id}/download` | MP4 concluído via FileResponse |
| GET `/health` ou `/api/v1/health` | Diagnóstico de integridade (SQLite, disco, FFmpeg, Whisper, LLM) |
| GET `/healthz` | Probe de liveness leve para orquestradores (200 OK) |
| GET `/metrics` | Métricas no padrão de texto Prometheus |
| GET `/api/v1/metrics` | Métricas consolidadas em formato JSON |

Campos multipart: `video_file`, `transcription_mode`, `style_preset`, `external_subtitle_file`, `language`, `custom_style` (JSON em string). `external` exige arquivo de legenda. Exemplo em PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/subtitles/generate -F "video_file=@video.mp4" -F "transcription_mode=external" -F "external_subtitle_file=@legenda.srt" -F "style_preset=movie_series"
curl.exe http://127.0.0.1:8000/api/v1/jobs/COLE-O-JOB-ID
curl.exe -o resultado.mp4 http://127.0.0.1:8000/api/v1/jobs/COLE-O-JOB-ID/download
```

Erros: 422 parâmetros/arquivo inválidos, 413 limite de upload (soma dos arquivos, padrão 500 MB decimais), 404 job/saída ausente, 409 download antes da conclusão ou após falha. O limite é verificado ao salvar os arquivos após o parser multipart; não substitui um limite de corpo de requisição em um proxy caso a aplicação seja futuramente publicada.

Uploads recebem nomes locais fixos em pasta exclusiva; nomes enviados não definem destinos. O conteúdo do MP4 é conferido com FFprobe antes de aceitar o job. BackgroundTasks executa o pipeline síncrono fora do event loop e limpa uploads ao terminar. A aplicação não carrega o modelo nem abre banco na importação; recursos são criados ao primeiro uso.

Validação de servidor real (inicia porta local temporária, faz upload/consulta/download e encerra):

```powershell
.\.venv\Scripts\python scripts/smoke_http.py --video entrada.mp4 --subtitles palavras.json --output resultado-http.mp4
```

O script usa preset Instagram, portanto requer JSON alinhado. A validação de entrega observou QUEUED → PROCESSING → COMPLETED, download MP4 e `/docs` 200. Veja [evidências](docs/validation.md).

## Observabilidade

A aplicação dispõe de instrumentação nativa para monitoramento e diagnóstico:

* **Logs contextuais com `job_id`**: O módulo `video_subtitleler.observability` fornece `get_logger`, `job_context` e `configure_logging`. Todo log emitido durante a execução de um job carrega automaticamente o `[job_id=...]` correspondente via `contextvars`. Suporta formatação padrão textual ou JSON para ingestão centralizada (Fluentbit, Datadog, CloudWatch).
* **Métricas Prometheus & JSON**: Middleware HTTP e pipeline rastreiam automaticamente:
  * `video_subtitles_jobs_active` (gauge)
  * `video_subtitles_jobs_total` (counter por status, modo e preset)
  * `video_subtitles_job_duration_seconds` (summary com contagem, soma, mín/máx/méd)
  * `video_subtitles_step_duration_seconds` (summary por etapa do pipeline)
  * `video_subtitles_http_requests_total` e `video_subtitles_http_request_duration_seconds`
  * Exportação disponível em `/metrics` (texto Prometheus padrão) e `/api/v1/metrics` (JSON estruturado).
* **Health Checks**:
  * `/healthz`: endpoint ultraleve de liveness probe para orquestradores (K8s/Docker).
  * `/health` e `/api/v1/health`: checagem de prontidão e diagnóstico com status de conectividade do SQLite, espaço livre em disco (`work_dir`/`output_dir`), presença dos binários `ffmpeg`/`ffprobe` e configurações do Whisper/LLM. Retorna 200 (healthy/degraded) ou 503 (unhealthy).

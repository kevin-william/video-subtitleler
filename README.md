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

## Transcrição Whisper

O modelo é carregado sob demanda com `word_timestamps=True`. Padrões: `small`, `cpu`, `int8`; configure `SUBTITLE_WHISPER_MODEL`, `SUBTITLE_WHISPER_DEVICE` e `SUBTITLE_WHISPER_COMPUTE_TYPE`. Um nome de modelo permite download pelo Faster-Whisper na primeira execução; um diretório de pesos local permite operação offline. A suíte usa somente pesos locais informados explicitamente.

O extra Whisper limita PyAV a `>=11,<17`: PyAV 19 removeu o argumento `metadata_errors` usado pelo Faster-Whisper 1.2.1. A combinação validada usa PyAV 16.1.0, registrada no lock. Resultado vazio ou alinhamento inválido gera erro claro; não altera tempos para forçar aprovação.

Teste real com voz autorizada e modelo já baixado:

```powershell
$env:SUBTITLE_TEST_MODEL = 'C:\caminho\para\pesos-locais'
$env:SUBTITLE_TEST_VOICE = 'C:\caminho\para\voz-em-ingles.wav'
.\.venv\Scripts\python -m pytest -m integration_whisper -q
```

O teste usa voz em inglês de pelo menos cinco palavras. A validação de entrega utilizou voz sintética local (Microsoft Zira) e Whisper tiny em CPU.

## Refinamento LLM e fallback

Configure `SUBTITLE_LLM_API_KEY`, `SUBTITLE_LLM_BASE_URL`, `SUBTITLE_LLM_MODEL` e `SUBTITLE_LLM_TIMEOUT` (30 s). Não há endpoint padrão apresentado como verificado. O cliente LangChain ChatOpenAI usa JSON mode, chave/endpoint/modelo configuráveis e zero retries. O timeout limita a chamada assíncrona; falhas, quota, indisponibilidade, JSON inválido ou quebra de identidade de palavras retornam a mesma trilha Whisper.

O modelo recebe ids e tempos, mas devolve somente ids/texto agrupado; os tempos são copiados localmente do original. Respostas com tempos extras, palavras ausentes, ids duplicados/fora de ordem ou expansão de uma palavra em várias são rejeitadas. Grupos LLM do Instagram têm 2–4 palavras, com sobra final menor.

O teste do SDK real usa um servidor OpenAI-compatible local. Credenciais e compatibilidade de um provedor externo concreto (incluindo OpenCode Go/DeepSeek) precisam ser verificadas no ambiente de uso. Sem configuração LLM, o modo híbrido continua com Whisper e marca a etapa LLM como SKIPPED. Logs de fallback não incluem exceções que possam revelar chaves.

## Cinema e séries

`movie_series`: texto branco, Arial configurável, contorno preto 2 px, sombra leve, alinhamento inferior central e no máximo duas linhas por evento. CPL padrão 40, configurável de 37 a 42. Com palavras, a divisão usa seus limites reais; com segmentos externos, blocos longos dividem o intervalo proporcionalmente ao texto, sem alegar sincronismo por palavra. Palavras maiores que CPL são quebradas para caber.

ASS usa centésimos e cores BGR. Intervalos que colapsam para duração zero nessa precisão são rejeitados. Barras invertidas e chaves de texto recebido são representadas por glifos de largura cheia para impedir interpretação como comandos ASS. Verifique a disponibilidade da fonte escolhida; a resolução ASS acompanha o vídeo.

## Instagram e música

`instagram_music`: Impact configurável, centro da tela, blocos de 2–5 palavras (sobra final menor), palavras inativas brancas com 85% de opacidade e palavra ativa ciano `#00FFCC` por padrão. O gerador usa eventos ASS por intervalo com overrides de cor/opacidade, em vez de tags de karaokê acumulativas: o destaque anterior desaparece e pausas não têm palavra ativa. Todas as palavras do bloco permanecem visíveis. Linhas são divididas por uma estimativa de largura para acomodar vídeos estreitos.

Overrides são compartilhados pela API/CLI. Não se oferece alinhamento forçado de SRT/VTT. A suíte verifica o movimento e a ausência do destaque durante pausa também nos pixels do vídeo renderizado.

## Renderização

FFmpeg com filtro `ass`/libass codifica H.264 e áudio AAC em MP4, preservando duração, dimensões de exibição e presença de áudio. O modo padrão usa CPU (`libx264`); `SUBTITLE_RENDER_ENCODER` aceita opcionalmente `h264_nvenc`, `h264_qsv` ou `h264_amf`, com verificação de disponibilidade e erro explícito se falhar. O filtro ASS pode permanecer em CPU. Hardware não foi validado nesta entrega.

O render usa diretório temporário próprio, nome de ASS controlado, argumentos sem shell e saída publicada somente após FFprobe validar o resultado. Isso evita interpolar caminhos Windows com espaços/apóstrofos na sintaxe do filtro. Falhas removem somente parciais próprios. O destino precisa ser novo.

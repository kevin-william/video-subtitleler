# Evidências de validação — 24/10/2026

Ambiente: Windows, Python 3.12.6, `.venv` sem pacotes globais; dependências exatas em [requirements-dev.lock](../requirements-dev.lock). `pip check`: No broken requirements found.

## Resultados

- Suíte final: **146 passed**, sem skips, com SUBTITLE_TEST_MODEL apontando para Whisper tiny local e SUBTITLE_TEST_VOICE para a voz sintética Microsoft Zira (en-US). Sem essas variáveis, o teste integration_whisper registra skip explícito.
- FFmpeg/FFprobe reais: MP4 sintético, áudio mono PCM 16 kHz, render dos dois estilos, preservação de vídeo/áudio e caminhos Windows com espaços/acentos/apóstrofos.
- Teste de pixels: a região ciano muda da primeira para a segunda palavra e some durante a pausa. Quadros de cinema e karaokê também foram inspecionados visualmente.
- Whisper real: reconheceu “Hello World. This is a subtitle synchronization test. Each word should appear at the correct time.”, com 16 palavras temporizadas. Amostra gerada localmente por System.Speech/Microsoft Zira.
- Pipeline real: whisper_only nos dois presets e llm_hybrid sem provedor, que concluiu com fallback e etapa LLM SKIPPED.
- Cliente LangChain/ChatOpenAI real: JSON mode validado contra servidor local OpenAI-compatible. Falhas, timeout, respostas inválidas e alteração de identidade cobertos com testes controlados.
- CLI real: processou a voz sintetizada com Whisper tiny e produziu MP4 Instagram; também há teste integrado external + FFmpeg.
- Uvicorn real em porta local temporária: POST 202, estados observados QUEUED → PROCESSING → COMPLETED, download MP4 (117.020 bytes na execução registrada), /docs 200 e servidor encerrado ao terminar. O tamanho de amostras posteriores pode variar.
- Todas as 12 tarefas aprovadas no verificador de trechos literais.

## Reprodução

Seguir instalação e configuração no [README](../README.md). Executar `python -m pytest -q` com as duas variáveis de recursos locais para incluir Whisper real. `scripts/smoke_demo.py` gera novas amostras preservando execuções anteriores; `scripts/smoke_http.py` testa o servidor real e encerra ao terminar.

O Whisper tiny foi baixado para `.models/`, ignorado pelo Git; não há download de pesos na suíte padrão. As amostras ficaram em `output/demo/run-d1y5lizn/` no ambiente local (também ignoradas), com transcript.json, ASS, MP4 e evidence.json. Cli-result.mp4 usa a revisão final de espaços ASS; outras amostras registram a execução original.

## Gates ainda externos

OpenCode Go/MiniMax foi validado com chamadas externas sintéticas conforme registro abaixo; outros provedores não foram verificados. A renderização com NVENC não foi executada; a transcrição CUDA foi validada conforme registro abaixo. A inspeção automatizada e de quadros não substitui a aprovação humana do vídeo em player. Estes limites não impedem o uso do fluxo CPU/Whisper ou external validado.

## Validação adicional da RTX 3050 — 24/10/2026

- GPU: NVIDIA GeForce RTX 3050 6GB Laptop GPU, 6144 MiB, driver 617.14. CTranslate2 4.8.3 reconheceu uma GPU e suporte a `float16`.
- O ambiente `C:\workspace\python\.venv` contém PyTorch 2.9.0+cu130 e DLLs CUDA 13; não contém Faster-Whisper. O primeiro teste no ambiente do projeto falhou por ausência de `cublas64_12.dll`. As bibliotecas compatíveis CUDA 12/cuDNN 9 foram instaladas somente na `.venv` deste projeto; versões em `requirements-cuda.lock`.
- O adaptador registra as pastas de DLLs dos pacotes NVIDIA do ambiente atual ao carregar Whisper em CUDA no Windows. Não altera o PATH global nem depende da `.venv` compartilhada.
- `.env` local configurado para `cuda`/`float16` e pesos locais de `Systran/faster-whisper-small`, revisão `536b0662742c02347bc0e980a01041f333bce120`, baixados em `.models/`.
- Transcrição real pela classe `Transcriber`, usando `Settings()` do `.env` e `output/demo/voice.wav`: dispositivo efetivo `cuda`, cálculo `float16`, 16 palavras com timestamps; texto: “Hello world. This is a subtitle synchronization test. Each word should appear at the correct time.”
- Tempo observado: 11,29 s incluindo carga do modelo. Memória total da GPU observada após transcrição: 731 MiB. São medições de uma amostra curta, sem garantia de consumo ou desempenho em vídeos longos.
- Suíte final com `SUBTITLE_TEST_DEVICE=cuda`, `SUBTITLE_TEST_COMPUTE_TYPE=float16`, modelo small e voz locais: **147 passed** em 10,41 s, sem skips. `pip check`: No broken requirements found.

## OpenCode Go / MiniMax — 24/10/2026

- Chave fornecida pelo usuário no `.env`, mantida fora de logs e do Git. Modelo `minimax-m3.1-flash`; base URL `https://opencode.ai/inference/go/openai/v1`. Escolhido como a opção MiniMax de menor preço na documentação Go consultada nesta data.
- Cliente ChatOpenAI com JSON mode, zero retries e timeout de 30 s. Identificação verdadeira `video-subtitleler/0.1.0` e UUID em `x-opencode-session` por refinamento.
- Duas chamadas externas reais, sem fallback, com oito palavras sintéticas em português: cinema em 15,04 s e Instagram em 1,94 s. IDs completos e ordenados, nenhum timestamp alterado, grupos Instagram de quatro palavras. Cinema corrigiu acentos e pontuação; Instagram corrigiu “ola” para “olá”, mas manteve “e” onde o contexto pedia “é”. A aceitação estrutural não garante correção linguística completa.
- Go é documentado para tráfego de agentes de programação. As chamadas de legenda sintética foram aceitas, mas não comprovam suporte contínuo a esta categoria de aplicação. Nenhum cabeçalho imita agente de terceiros.
- Suíte final, incluindo integração Whisper small/CUDA e testes locais do cliente LLM: **148 passed** em 9,52 s, sem skips. A suíte não faz chamadas externas à LLM; estas foram verificadas separadamente. `pip check` sem conflitos.

## Serviço em execução — 26/10/2026

Verificação feita contra o processo já ativo em `http://127.0.0.1:8000`, usando o MP4 sintético local `output/demo/run-d1y5lizn/input.mp4` (7,71 s). `/docs` e `/openapi.json` retornaram 200; `/` retorna 404 porque não existe página inicial configurada.

| Modo | Upload | Resultado | Tempo até concluir | Download |
|---|---|---|---|---|
| external | 202 | COMPLETED | 1,25 s | 200 |
| whisper_only | 202 | COMPLETED | 6,58 s | 200 |
| llm_hybrid | 202 | COMPLETED, LLM COMPLETED | 6,11 s | 200 |

Consultas de progresso responderam durante o processamento. Os três arquivos baixados passaram pelo FFprobe: vídeo H.264 1280×720, áudio AAC, duração 7,708980 s. Evidências e MP4s em `output/diagnostics/20261026-173724/`; o modo híbrido chamou a LLM de fato, sem fallback. São testes curtos e não comprovam desempenho ou correção de vídeos arbitrários.

Suíte executada separadamente: **147 passed, 1 skipped**, em 6,20 s. O skip corresponde ao teste Whisper real sem as variáveis de recursos locais; a transcrição real foi exercitada nos uploads HTTP acima. Nenhuma alteração funcional foi feita no serviço durante este diagnóstico.

Respostas a entradas inválidas também verificadas: upload ausente 422, MP4 inválido 422, job inexistente 404.

## Ajustes encontrados na validação

PyAV 19 removeu metadata_errors de av.open, ainda usado por Faster-Whisper 1.2.1. O extra Whisper limita av>=11,<17 e o lock registra 16.1.0 validado. A instalação limpa por pip com acesso à rede substituiu a instalação provisória da T01 que utilizava dependências globais. Nenhum pacote do Python global foi alterado.

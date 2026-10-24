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

Não houve chamada a OpenCode Go/DeepSeek nem outro provedor LLM externo: faltam endpoint/credenciais configurados. Aceleração de hardware não foi executada. A inspeção automatizada e de quadros não substitui a aprovação humana do vídeo em player. Estes limites não impedem o uso do fluxo CPU/Whisper ou external validado.

## Ajustes encontrados na validação

PyAV 19 removeu metadata_errors de av.open, ainda usado por Faster-Whisper 1.2.1. O extra Whisper limita av>=11,<17 e o lock registra 16.1.0 validado. A instalação limpa por pip com acesso à rede substituiu a instalação provisória da T01 que utilizava dependências globais. Nenhum pacote do Python global foi alterado.

# T04 — Transcrever com Faster-Whisper e tempos por palavra

> **Instruções do projeto:** consultar [contexto e convenções](index.md#contexto-e-convenções) e preservar as instruções AGENTS fornecidas na sessão.

> **Status:** Concluída; gates externos documentados
> **Progresso:** 100%
> **Início:** 24/10/2026 | **Fim previsto:** - | **Fim real:** 24/10/2026
> **Responsável:** Codex
> **Dependências:** [T01](t01-base-contratos-configuracao.md), [T02](t02-extracao-audio.md)
> **Commit único:** `feat(transcription): add faster whisper adapter`

## 1. Por que

Fornecer o resultado temporal nativo que atende whisper_only e serve de fallback confiável ao modo híbrido.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trechos literais; escolhas e complementos de implementação aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
## 2. Decisões Técnicas Alinhadas

| Componente | Tecnologia Escolhida | Justificativa |
| :--- | :--- | :--- |
| **Framework Web** | `FastAPI` + `Uvicorn` | Alto desempenho, suporte assíncrono nativo, OpenAPI docs automática e tipagem estrita com Pydantic v2. |
| **CLI Local** | `Typer` + `Rich` | Permite testes rápidos locais, scripts automatizados e interface com barras de progresso elegantes. |
| **Transcrição Base** | `faster-whisper` (CTranslate2) | Até 4x mais rápido que o Whisper original, menor consumo de VRAM/RAM e timestamps por palavra nativos (`word_timestamps=True`). |
| **Refinamento com LLM** | `LangChain` (`ChatOpenAI`) | Flexível e agnóstico: suporta **OpenCode Go** (`base_url` customizada) e **DeepSeek** (V3/R1) sem dependência de vendor lock-in. |
| **Resiliência LLM** | Fallback transparente | Se a LLM falhar (timeout, cota, erro de conexão), o sistema utiliza diretamente os timestamps do Whisper sem interromper o job. |
| **Motor de Renderização** | `FFmpeg` com filtro `ass` | Processamento via C altamente otimizado; evita o gargalo de bibliotecas frame-a-frame em Python (`MoviePy`/`OpenCV`) que seriam 10x a 50x mais lentas. |
| **Formato de Estilo** | `ASS` (Advanced SubStation Alpha) | Padrão da indústria para animações de texto, suporte a tags de karaokê (`\k`), cores hexadecimais BGR, rotações e outlines. |

---
````
<!-- PLAN_EXCERPT_END -->

<!-- PLAN_EXCERPT_START -->
````text
## 4. Estrutura do Projeto

```
c:\workspace\python\video-subtitleler/
├── pyproject.toml              # Dependências e empacotamento com Poetry/Pip
├── README.md                   # Documentação de instalação e uso
├── .env.example                # Configuração de variáveis de ambiente
├── src/
│   └── video_subtitleler/
│       ├── __init__.py
│       ├── config.py           # Configurações gerais (Pydantic Settings)
│       ├── models/
│       │   ├── __init__.py
│       │   ├── schema.py       # Pydantic Schemas (Job, SubtitleRequest, Presets)
│       │   └── subtitles.py    # Modelos de dados (Word, Segment, SubtitleTrack)
│       ├── services/
│       │   ├── __init__.py
│       │   ├── audio.py        # Extração e normalização de áudio via FFmpeg
│       │   ├── transcriber.py  # Wrapper Faster-Whisper
│       │   ├── llm_enhancer.py # LangChain pipeline (OpenCode Go / DeepSeek) com Fallback
│       │   ├── ass_builder.py  # Construtor de arquivos ASS (Cinema vs Instagram Karaoke)
│       │   └── renderer.py     # Queima de legendas com FFmpeg
│       ├── storage/
│       │   ├── __init__.py
│       │   └── job_store.py    # Repositório de estado de jobs (SQLite / Memória)
│       ├── api/
│       │   ├── __init__.py
│       │   ├── app.py          # Instância do FastAPI e middlewares
│       │   ├── routes.py       # Endpoints (/jobs, /upload, /status, /download)
│       │   └── dependencies.py # Injeção de dependências
│       └── cli/
│           ├── __init__.py
│           └── main.py         # Interface CLI via Typer
└── tests/
    ├── test_ass_builder.py     # Testes de geração de scripts ASS
    ├── test_llm_enhancer.py    # Testes do LangChain com mock e fallback
    ├── test_pipeline.py        # Testes de integração de ponta a ponta
    └── test_api.py             # Testes dos endpoints HTTP da FastAPI
```

---
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Todos os arquivos de produção/teste abaixo são criações propostas ou extensões de tarefas predecessoras, pois ainda não existem no repositório. Nomes de testes são módulos pytest propostos, não classes existentes verificadas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/services/transcriber.py | Criar adaptador de Faster-Whisper |
| Teste | tests/test_transcriber.py | Criar testes de contrato e integração opcional com voz |
| Documentação | README.md | Documentar modelos, idioma e download dos pesos |

Atualizar o status desta tarefa e o [índice](index.md) no mesmo commit de entrega.

## 4. Como implementar

1. Carregar o modelo sob demanda por fábrica injetável, respeitando configuração de dispositivo/modelo e sem exigir GPU.
2. Transcrever o WAV de T02 com word_timestamps=True; transformar o iterador do provedor nos modelos de T01 e preservar início/fim de cada palavra.
3. Mapear language=auto para detecção e aceitar código explícito. Tratar resultado vazio, erro de carregamento e erro durante consumo do iterador com diagnósticos claros.
4. Definir política explícita para segmentos sem palavras: aceitar texto segmentado para cinema, mas não anunciar suporte a karaokê sem alinhamento válido.

Manter o pacote importável e os predecessores funcionando ao concluir. A reversão deste commit deve preservar os predecessores; reverter consumidores posteriores primeiro, se já existirem.

## 5. Testes no mesmo commit

- Mockar modelo/iterador para verificar parâmetros, idioma automático/explícito e preservação dos tempos.
- Cobrir áudio silencioso, palavras ausentes e falha tardia do iterador.
- Oferecer teste integration_whisper com áudio de voz autorizado e pesos locais, sem rede no teste padrão; registrar origem do fixture e skip se faltar recurso.

Código e testes são inseparáveis nesta tarefa. Testes unitários usam doubles nos limites externos; integrações reais são identificadas e relatadas separadamente, com skips explícitos quando seus recursos não existirem.

## 6. Validação

Executar da raiz após instalar o projeto com `python -m pip install -e ".[dev]"` (a instalação é entregue em T01):

```powershell
python -m pytest tests/test_transcriber.py -m "not integration_whisper"
python -m pytest tests/test_audio.py tests/test_models.py
python scripts/verify_plan_excerpts.py tasks
```

Relatar comandos executados, resultados e gates pendentes. Servidor manual não conta como teste automatizado aprovado.

## 7. Gates e fora do escopo

- Download de pesos, espaço e execução real em CPU/GPU dependem do ambiente. Mock não comprova qualidade de reconhecimento.
- Fora do escopo: correção LLM, diarização, tradução e otimização de GPU.
- Implementar apenas o comportamento desta tarefa; não antecipar consumidores das tarefas seguintes.
- A documentação de tarefas não comprova implementação ou execução dos testes de produção.

## 8. Critérios de aceite (DoD)

- [x] Comportamento de produção descrito implementado e importável.
- [x] Testes automatizados desta tarefa entregues no mesmo commit e aprovados; skips/gates relatados.
- [x] Documentação diretamente afetada atualizada.
- [x] Trechos literais validados por `scripts/verify_plan_excerpts.py`.
- [x] Dependências, limites de escopo e regressões dos predecessores conferidos.
- [x] Um único commit criado com a mensagem prevista, com status desta tarefa e índice atualizados.

---
## Status de implementação da tarefa

| Item | Status |
|---|---|
| Implementação | Concluída |
| Testes | Automatizados aprovados; gates relatados |
| Documentação de implementação | README e contratos atualizados |
| Validação do usuário | Pendente |

**Progresso geral:** 100%

## Registro de execução — 24/10/2026

Implementação e testes entregues no mesmo commit previsto. O snapshot isolado deste commit foi validado com `python -m pytest -q tests/test_transcriber.py` antes do registro. Referências literais e links permanecem válidos.

Whisper tiny em CPU/int8 transcreveu a voz sintética local Microsoft Zira. Teste real com SUBTITLE_TEST_MODEL e SUBTITLE_TEST_VOICE aprovou. A quebra de PyAV 19 foi detectada e o extra passou a limitar versões; PyAV 16.1.0 foi validado.

Validação humana em player e uso com provedor LLM externo continuam pendentes conforme os gates do índice; não foram apresentados como aprovação automática.


# T01 — Criar pacote, contratos e configuração validada

> **Instruções do projeto:** consultar [contexto e convenções](index.md#contexto-e-convenções) e preservar as instruções AGENTS fornecidas na sessão.

> **Status:** Concluída; gates externos documentados
> **Progresso:** 100%
> **Início:** 24/10/2026 | **Fim previsto:** - | **Fim real:** 24/10/2026
> **Responsável:** Codex
> **Dependências:** Nenhuma
> **Commit único:** `feat(core): define subtitle contracts and settings`

## 1. Por que

Fornecer uma biblioteca importável com contratos e configuração verificáveis. Modelos, configuração e empacotamento formam a base mínima consumível; nenhum serviço fictício deve ser criado para simular uma implementação pronta.

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
| Produção | pyproject.toml | Criar pacote src, dependências e extras de desenvolvimento |
| Produção | src/video_subtitleler/__init__.py | Criar identificação do pacote |
| Produção | src/video_subtitleler/config.py | Criar Settings com Pydantic Settings |
| Produção | src/video_subtitleler/models/__init__.py | Criar pacote |
| Produção | src/video_subtitleler/models/schema.py | Criar contratos de requisição, estilos e jobs |
| Produção | src/video_subtitleler/models/subtitles.py | Criar Word, Segment e SubtitleTrack |
| Teste | tests/test_models.py; tests/test_config.py | Criar testes unitários |
| Documentação | README.md; .env.example | Criar instalação, configuração e contratos |

Atualizar o status desta tarefa e o [índice](index.md) no mesmo commit de entrega.

## 4. Como implementar

1. Criar pyproject.toml com instalação editável por pip, Python 3.12 como escolha inicial e dependências indicadas no plano; disponibilizar pytest, httpx e ferramentas de teste no extra dev. Registrar o marcador pytest `integration_whisper` e garantir que os testes padrão não baixem pesos nem chamem provedores. Evitar baixar pesos de modelos na instalação ou ao importar o pacote.
2. Definir Word com texto e início/fim em segundos, Segment e SubtitleTrack com idioma e palavras opcionais. Validar tempos finitos, não negativos, fim maior que início e ordenação; documentar a política de sobreposição em vez de inferir correções silenciosas.
3. Definir enums de modos/presets, overrides de cores/fontes/tamanho/alinhamento, estados de job e respostas. Não exigir timestamps por palavra de uma legenda externa segmentada. Validar cor, tamanho e caminhos conforme contrato; regras que dependem de arquivos ficam nos consumidores.
4. Configurar caminhos de FFmpeg/FFprobe, diretórios de trabalho/saída, modelo Whisper e opções LLM (chave, base_url, modelo e timeout). Segredos não aparecem em logs ou exemplos reais. Não apresentar a URL do exemplo do plano como provedor já verificado.
5. Documentar escolhas propostas: CPL padrão 40 dentro da faixa 37–42; Instagram determinístico com 2–5 palavras e refinamento LLM com 2–4, admitindo bloco final menor; SQLite como persistência principal e memória como implementação de testes. Esses valores não são citações literais do plano.

Manter o pacote importável e os predecessores funcionando ao concluir. A reversão deste commit deve preservar os predecessores; reverter consumidores posteriores primeiro, se já existirem.

## 5. Testes no mesmo commit

- Construir trilhas e jobs válidos, testar serialização e rejeitar tempos inválidos, NaN, enums e overrides inválidos.
- Verificar carregamento e precedência de variáveis com ambiente isolado, valores padrão e proteção de segredos.
- Confirmar importação sem iniciar FFmpeg, acessar rede ou carregar Whisper.

Código e testes são inseparáveis nesta tarefa. Testes unitários usam doubles nos limites externos; integrações reais são identificadas e relatadas separadamente, com skips explícitos quando seus recursos não existirem.

## 6. Validação

Executar da raiz após instalar o projeto com `python -m pip install -e ".[dev]"` (a instalação é entregue em T01):

```powershell
python -m pip install -e ".[dev]"
python -m pytest tests/test_models.py tests/test_config.py
python scripts/verify_plan_excerpts.py tasks
```

Relatar comandos executados, resultados e gates pendentes. Servidor manual não conta como teste automatizado aprovado.

## 7. Gates e fora do escopo

- Versões concretas das dependências serão resolvidas durante a implementação e registradas de forma reproduzível; ainda não foram verificadas.
- Fora do escopo: serviços, interfaces e inicialização de Git. O commit exige repositório Git disponível.
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

Implementação e testes entregues no mesmo commit previsto. O snapshot isolado deste commit foi validado com `python -m pytest -q tests/test_models.py tests/test_config.py` antes do registro. Referências literais e links permanecem válidos.

A instalação isolada com todos os extras foi resolvida por pip com acesso à rede e sem usar pacotes globais; o problema inicial de DNS foi superado. O histórico Git local foi inicializado durante a autorização de execução de ponta a ponta; nenhum repositório remoto foi criado.

Validação humana em player e uso com provedor LLM externo continuam pendentes conforme os gates do índice; não foram apresentados como aprovação automática.


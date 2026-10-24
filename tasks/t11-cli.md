# T11 — Expor processamento local pela CLI

> **Instruções do projeto:** consultar [contexto e convenções](index.md#contexto-e-convenções) e preservar as instruções AGENTS fornecidas na sessão.

> **Status:** Concluída; gates externos documentados
> **Progresso:** 100%
> **Início:** 24/10/2026 | **Fim previsto:** - | **Fim real:** 24/10/2026
> **Responsável:** Codex
> **Dependências:** [T10](t10-pipeline-integrado.md)
> **Commit único:** `feat(cli): expose subtitle processing commands`

## 1. Por que

Disponibilizar uso local completo dos modos e presets pelo ponto de entrada documentado no plano.

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
## 7. Plano de Verificação

### Testes Automatizados
* **`tests/test_ass_builder.py`**:
  * Verifica se o arquivo `.ass` gerado contém os cabeçalhos corretos (`[V4+ Styles]` e `[Events]`).
  * Valida que o estilo `instagram_music` inclui as tags de tempo e destaque de palavras.
  * Valida que o estilo `movie_series` respeita as quebras de linha padrão.
* **`tests/test_llm_enhancer.py`**:
  * Testa o fluxo de enriquecimento com mock da API.
  * Testa o mecanismo de fallback quando a LLM gera exceção ou timeout.
* **`tests/test_api.py`**:
  * Testa o ciclo de vida dos jobs via TestClient do FastAPI.

### Verificação Manual
1. Gerar um vídeo curto de teste `.mp4` sintético via FFmpeg com áudio de voz.
2. Executar via CLI nos dois modos:
   - `python -m video_subtitleler.cli process video_teste.mp4 --style movie_series`
   - `python -m video_subtitleler.cli process video_teste.mp4 --style instagram_music`
3. Iniciar o servidor FastAPI (`uvicorn video_subtitleler.api.app:app`) e testar via Swagger UI (`/docs`).
4. Inspecionar o vídeo resultante em player para confirmar sincronismo e fidelidade visual.
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Todos os arquivos de produção/teste abaixo são criações propostas ou extensões de tarefas predecessoras, pois ainda não existem no repositório. Nomes de testes são módulos pytest propostos, não classes existentes verificadas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/cli/__init__.py; src/video_subtitleler/cli/__main__.py; src/video_subtitleler/cli/main.py | Criar módulo executável e comando Typer/Rich |
| Produção | pyproject.toml | Registrar comando de console opcional |
| Teste | tests/test_cli.py | Criar testes com CliRunner |
| Documentação | README.md; .env.example | Documentar instalação, exemplos e falhas |

Atualizar o status desta tarefa e o [índice](index.md) no mesmo commit de entrega.

## 4. Como implementar

1. Implementar python -m video_subtitleler.cli process, acrescentando __main__.py necessário embora ausente na árvore proposta.
2. Expor vídeo, saída, transcription_mode, style, legenda externa, idioma e overrides documentados; escolher whisper_only como padrão local explícito para funcionar sem chave LLM.
3. Usar o pipeline compartilhado, mostrar etapas/progresso com Rich e informar destino final; retornar códigos de saída diferentes para sucesso e erro sem imprimir segredos.
4. Garantir que --help funcione sem pesos, credenciais ou executáveis de mídia. Validar combinação external sem arquivo antes de iniciar trabalho.

Manter o pacote importável e os predecessores funcionando ao concluir. A reversão deste commit deve preservar os predecessores; reverter consumidores posteriores primeiro, se já existirem.

## 5. Testes no mesmo commit

- Usar CliRunner com pipeline injetado para sucesso dos três modos, opções, ajuda e códigos de saída.
- Cobrir arquivo ausente, override inválido, external sem legenda e erro propagado do pipeline.
- Executar comando real external em MP4 sintético; comandos com fala dos dois presets entram no checklist manual com recursos reais.

Código e testes são inseparáveis nesta tarefa. Testes unitários usam doubles nos limites externos; integrações reais são identificadas e relatadas separadamente, com skips explícitos quando seus recursos não existirem.

## 6. Validação

Executar da raiz após instalar o projeto com `python -m pip install -e ".[dev]"` (a instalação é entregue em T01):

```powershell
python -m pytest tests/test_cli.py
python -m video_subtitleler.cli --help
python -m pytest tests/test_pipeline.py
python scripts/verify_plan_excerpts.py tasks
```

Relatar comandos executados, resultados e gates pendentes. Servidor manual não conta como teste automatizado aprovado.

## 7. Gates e fora do escopo

- Exemplos manuais do plano omitem modelo/credenciais; README deve explicar o modo padrão escolhido e pré-requisitos.
- Fora do escopo: servidor HTTP, interface gráfica e novos presets.
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

Implementação e testes entregues no mesmo commit previsto. O snapshot isolado deste commit foi validado com `python -m pytest -q tests/test_cli.py` antes do registro. Referências literais e links permanecem válidos.

CliRunner cobriu sucesso, parâmetros inválidos e código de falha. CLI real com Whisper tiny e voz sintética gerou MP4 Instagram; integração external + FFmpeg também aprovada.

Validação humana em player e uso com provedor LLM externo continuam pendentes conforme os gates do índice; não foram apresentados como aprovação automática.


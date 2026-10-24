# T03 — Importar legendas SRT, VTT e JSON

> **Instruções do projeto:** consultar [contexto e convenções](index.md#contexto-e-convenções) e preservar as instruções AGENTS fornecidas na sessão.

> **Status:** Concluída; gates externos documentados
> **Progresso:** 100%
> **Início:** 24/10/2026 | **Fim previsto:** - | **Fim real:** 24/10/2026
> **Responsável:** Codex
> **Dependências:** [T01](t01-base-contratos-configuracao.md)
> **Commit único:** `feat(subtitles): import external subtitle tracks`

## 1. Por que

Tornar o modo external um produtor independente de SubtitleTrack, sem dependência de Whisper ou de serviços LLM.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trechos literais; escolhas e complementos de implementação aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
## 1. Visão Geral da Arquitetura

O sistema adota uma arquitetura em camadas desacopladas:

```mermaid
flowchart TD
    subgraph Interfaces ["Interfaces de Entrada"]
        CLI["CLI Utilitária (Typer/Rich)"]
        API["API REST (FastAPI)"]
    end

    subgraph JobManager ["Gerenciamento de Jobs"]
        Queue["Fila de Tarefas Assíncronas (BackgroundTasks)"]
        Store["Repositório de Jobs (SQLite / Memória)"]
    end

    subgraph TranscriptionLayer ["Camada de Transcrição e Sincronismo"]
        Router{"Modo de Legenda?"}
        Ext["Legenda Externa (.srt, .vtt, .json)"]
        WOnly["Whisper Direto (Faster-Whisper)"]
        HLLM["Pipeline Híbrido (Whisper + LangChain LLM)"]
        Fallback["Fallback Automático (Whisper puro)"]
    end

    subgraph StylingLayer ["Camada de Estilização & Geração ASS"]
        MovieStyle["Preset Cinema / Séries (CPL seguro, inferior)"]
        InstaStyle["Preset Instagram / Música (Karaokê palavra ativa)"]
        ASSGen["Gerador de Script ASS (Advanced SubStation Alpha)"]
    end

    subgraph RenderingLayer ["Motor de Renderização"]
        FFmpeg["FFmpeg (Filtro ASS com aceleração de hardware opcional)"]
        OutputMP4["Vídeo Final (.mp4)"]
    end

    CLI --> Router
    API --> Queue --> Store --> Router

    Router -->|external| Ext
    Router -->|whisper_only| WOnly
    Router -->|llm_hybrid| HLLM
    HLLM -.->|se falhar/timeout| Fallback

    Ext --> StylingLayer
    WOnly --> StylingLayer
    HLLM --> StylingLayer
    Fallback --> StylingLayer

    MovieStyle --> ASSGen
    InstaStyle --> ASSGen
    ASSGen --> FFmpeg
    FFmpeg --> OutputMP4
```

---
````
<!-- PLAN_EXCERPT_END -->

<!-- PLAN_EXCERPT_START -->
````text
## 5. Especificação da API REST (FastAPI)

### Endpoints Principais

1. **`POST /api/v1/subtitles/generate`** (Multipart/Form-Data)
   * **Parâmetros**:
     * `video_file`: Arquivo `.mp4`
     * `transcription_mode`: `"llm_hybrid"` | `"whisper_only"` | `"external"`
     * `style_preset`: `"movie_series"` | `"instagram_music"`
     * `external_subtitle_file`: Opcional (`.srt`, `.vtt`, `.json`) se o modo for `"external"`
     * `language`: Código ISO (ex: `"pt"`, `"en"` ou `"auto"`)
     * `custom_style`: JSON opcional para sobreposição de cores, fontes e tamanhos
   * **Resposta (202 Accepted)**:
     ```json
     {
       "job_id": "c7a8b8c2-3e4b-4a55-89f1-d52b1b3b2c1a",
       "status": "QUEUED",
       "created_at": "2026-10-24T14:10:00Z",
       "message": "Job aceito para processamento em background."
     }
     ```

2. **`GET /api/v1/jobs/{job_id}`**
   * **Resposta (200 OK)**:
     ```json
     {
       "job_id": "c7a8b8c2-3e4b-4a55-89f1-d52b1b3b2c1a",
       "status": "PROCESSING",
       "progress_pct": 65,
       "current_step": "burning_subtitles",
       "steps": {
         "extract_audio": "COMPLETED",
         "transcription": "COMPLETED",
         "llm_enhancement": "COMPLETED",
         "generate_ass": "COMPLETED",
         "burning_subtitles": "RUNNING"
       },
       "error": null
     }
     ```

3. **`GET /api/v1/jobs/{job_id}/download`**
   * Retorna o arquivo `.mp4` legendado pronto para streaming ou download via `FileResponse`.

---
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Todos os arquivos de produção/teste abaixo são criações propostas ou extensões de tarefas predecessoras, pois ainda não existem no repositório. Nomes de testes são módulos pytest propostos, não classes existentes verificadas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/services/external_subtitles.py | Criar leitor e normalização; arquivo adicional ao esboço do plano |
| Teste | tests/test_external_subtitles.py; tests/fixtures/subtitles/ | Criar casos de importação |
| Documentação | README.md | Publicar formatos aceitos e exemplo JSON |

Atualizar o status desta tarefa e o [índice](index.md) no mesmo commit de entrega.

## 4. Como implementar

1. Fixar e documentar o contrato JSON usando a serialização de SubtitleTrack de T01, com segmentos e palavras opcionais. O plano lista a extensão, mas não define seu esquema; tratar isso como escolha de implementação.
2. Ler SRT e WebVTT respeitando seus timestamps, Unicode e múltiplas linhas; escolher parser mantido durante a implementação e declarar a dependência no pyproject.toml se necessário.
3. Rejeitar extensão, conteúdo vazio, tempos inválidos e estrutura JSON incompatível. Preservar tempos; não inventar alinhamento de palavras.
4. Definir a política para external com Instagram sem palavras: rejeitar a combinação com mensagem clara até existir alinhamento real. SRT/VTT segmentados continuam suportados no preset cinema. Permitir JSON com palavras válidas para karaokê.

Manter o pacote importável e os predecessores funcionando ao concluir. A reversão deste commit deve preservar os predecessores; reverter consumidores posteriores primeiro, se já existirem.

## 5. Testes no mesmo commit

- Importar exemplos mínimos válidos dos três formatos e comparar texto e tempos exatos.
- Cobrir BOM/acentos, múltiplas linhas, JSON com palavras, tempos inválidos e conteúdo que não corresponde à extensão.
- Confirmar preservação de precisão temporal e ausência de timestamps de palavras fabricados.

Código e testes são inseparáveis nesta tarefa. Testes unitários usam doubles nos limites externos; integrações reais são identificadas e relatadas separadamente, com skips explícitos quando seus recursos não existirem.

## 6. Validação

Executar da raiz após instalar o projeto com `python -m pip install -e ".[dev]"` (a instalação é entregue em T01):

```powershell
python -m pytest tests/test_external_subtitles.py
python -m pytest tests/test_models.py
python scripts/verify_plan_excerpts.py tasks
```

Relatar comandos executados, resultados e gates pendentes. Servidor manual não conta como teste automatizado aprovado.

## 7. Gates e fora do escopo

- Política external + Instagram sem palavras é escolha explícita para uma lacuna do plano; eventual alinhamento forçado é evolução separada.
- Fora do escopo: upload HTTP, reconhecimento de voz e acesso remoto a legendas.
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

Implementação e testes entregues no mesmo commit previsto. O snapshot isolado deste commit foi validado com `python -m pytest -q tests/test_external_subtitles.py` antes do registro. Referências literais e links permanecem válidos.

SRT/VTT usam parser local estrito de cues textuais, sem dependência adicional. STYLE/REGION/posicionamento não são preservados. JSON com palavras preserva os tempos; formatos externos não fabricam alinhamento.

Validação humana em player e uso com provedor LLM externo continuam pendentes conforme os gates do índice; não foram apresentados como aprovação automática.


# T12 — Expor geração assíncrona, consulta e download pela API

> **Instruções do projeto:** consultar [contexto e convenções](index.md#contexto-e-convenções) e preservar as instruções AGENTS fornecidas na sessão.

> **Status:** Não iniciada
> **Progresso:** 0%
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** A definir
> **Dependências:** [T10](t10-pipeline-integrado.md)
> **Commit único:** `feat(api): expose background subtitle jobs and downloads`

## 1. Por que

Entregar o ciclo HTTP completo em um commit: aceitar um job só tem valor com execução, consulta e download testados juntos.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trechos literais; escolhas e complementos de implementação aparecem fora dos marcadores.

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
| Produção | src/video_subtitleler/api/__init__.py; src/video_subtitleler/api/app.py; src/video_subtitleler/api/routes.py; src/video_subtitleler/api/dependencies.py | Criar FastAPI, injeção e três endpoints |
| Produção | pyproject.toml | Declarar dependências multipart se ainda faltarem |
| Teste | tests/test_api.py | Criar testes de ciclo de vida e uploads |
| Documentação | README.md; .env.example | Documentar Uvicorn, Swagger e contrato HTTP |

Atualizar o status desta tarefa e o [índice](index.md) no mesmo commit de entrega.

## 4. Como implementar

1. Implementar POST /api/v1/subtitles/generate multipart com parâmetros do plano e custom_style como JSON validado; salvar upload em diretório exclusivo sem confiar no nome enviado.
2. Persistir QUEUED e responder 202 com job_id/status/created_at/message. Agendar pipeline bloqueante com BackgroundTasks usando execução apropriada fora do event loop; evitar carregar o modelo durante importação da app.
3. Implementar GET /api/v1/jobs/{job_id} com progresso/etapas/erro e GET /api/v1/jobs/{job_id}/download com FileResponse somente após conclusão e arquivo existente.
4. Fixar contrato adicional de erros e documentá-lo: 422 para parâmetros/combinações inválidos, 404 para job ou saída inexistente e 409 para download antes da conclusão. Esses códigos adicionais são escolhas, não requisitos literais do plano.
5. Validar extensão/conteúdo de entrada, limites configurados de upload e limpeza em falhas; não aceitar caminhos arbitrários como destino nem retornar segredos em erro.
6. Usar rotas exatas da seção 5 como contrato público; os nomes genéricos /upload e /status no comentário da árvore não exigem endpoints adicionais. Documentar limitação de BackgroundTasks e armazenamento local.

Manter o pacote importável e os predecessores funcionando ao concluir. A reversão deste commit deve preservar os predecessores; reverter consumidores posteriores primeiro, se já existirem.

## 5. Testes no mesmo commit

- TestClient com dependências substituídas: POST 202, consulta QUEUED/PROCESSING/COMPLETED/FAILED e download com bytes, media type e nome corretos.
- Controlar executor no teste para observar QUEUED antes de executar background; TestClient pode aguardar BackgroundTasks e mascarar essa etapa.
- Cobrir multipart inválido, JSON inválido, external sem arquivo, job desconhecido, download pendente/fracassado/ausente, upload indevido e falha de pipeline.
- Executar integração HTTP + pipeline external + FFmpeg e regressão completa disponível. Abrir /docs e inspecionar manualmente vídeos dos dois presets.

Código e testes são inseparáveis nesta tarefa. Testes unitários usam doubles nos limites externos; integrações reais são identificadas e relatadas separadamente, com skips explícitos quando seus recursos não existirem.

## 6. Validação

Executar da raiz após instalar o projeto com `python -m pip install -e ".[dev]"` (a instalação é entregue em T01):

```powershell
python -m pytest tests/test_api.py
python -m pytest -m "not integration_whisper"
python -m uvicorn video_subtitleler.api.app:app
python scripts/verify_plan_excerpts.py tasks
```

Relatar comandos executados, resultados e gates pendentes. Servidor manual não conta como teste automatizado aprovado.

## 7. Gates e fora do escopo

- Uvicorn é verificação manual de servidor e deve ser encerrado após validar /docs; não é comando de teste que termina sozinho.
- Provedor LLM, reconhecimento real e inspeção humana continuam gates separados quando recursos faltarem.
- Fora do escopo: autenticação, publicação, hospedagem, workers distribuídos e garantia de retomada após reinício.
- Implementar apenas o comportamento desta tarefa; não antecipar consumidores das tarefas seguintes.
- A documentação de tarefas não comprova implementação ou execução dos testes de produção.

## 8. Critérios de aceite (DoD)

- [ ] Comportamento de produção descrito implementado e importável.
- [ ] Testes automatizados desta tarefa entregues no mesmo commit e aprovados; skips/gates relatados.
- [ ] Documentação diretamente afetada atualizada.
- [ ] Trechos literais validados por `scripts/verify_plan_excerpts.py`.
- [ ] Dependências, limites de escopo e regressões dos predecessores conferidos.
- [ ] Um único commit criado com a mensagem prevista, com status desta tarefa e índice atualizados.

---
## Status de implementação da tarefa

| Item | Status |
|---|---|
| Implementação | Não iniciada |
| Testes | Não iniciados |
| Documentação de implementação | Não iniciada |
| Validação do usuário | Pendente |

**Progresso geral:** 0%

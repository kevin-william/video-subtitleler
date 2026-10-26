# W02 — Enviar MP4 e concluir o primeiro ciclo pelo navegador

> **Instruções do projeto:** manter o [contexto e convenções](index.md#contexto-e-convenções) e as instruções AGENTS fornecidas na sessão.

> **Status:** Não iniciada
> **Progresso:** 0%
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** A definir
> **Dependências:** [W01](w01-pagina-assets-configuracao.md)
> **Commit único:** `feat(web): submit videos and track subtitle jobs`

## 1. Por que

Entregar valor de ponta a ponta com Whisper ou LLM: enviar um vídeo, consultar estado e baixar resultado. Formulário, transporte e monitoramento mínimo não ficam separados de seus testes.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trecho literal e contíguo da seção 4. Escolhas adicionais aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
## 4. W02 — Primeiro ciclo utilizável com Whisper e LLM

Entregar um fluxo completo inicial: selecionar/arrastar um MP4, escolher `whisper_only` ou `llm_hybrid`, escolher `movie_series` ou `instagram_music`, enviar, acompanhar status textual e obter um link de download quando concluído. Padrões: `whisper_only`, `movie_series`, idioma `auto`. Oferecer `pt`, `en`, `es` e código manual minúsculo de 2–3 letras, conforme o contrato real, sem prometer validação do catálogo ISO.

Validar extensão `.mp4` sem diferenciar maiúsculas, arquivo não vazio e tamanho em bytes segundo `ui-config`; MIME do navegador é apenas indicativo. Mostrar nome, tamanho e remoção do arquivo. Drag-and-drop deve ter alternativa por teclado. Se a configuração pública não puder ser obtida, bloquear novo envio com explicação e ação para tentar novamente.

Montar `FormData` com os nomes reais da API; `custom_style` será inicialmente `"{}"`. Não definir manualmente o Content-Type multipart. Bloquear duplo envio, validar 202 e UUID recebido e consultar apenas o job aceito; nunca repetir POST automaticamente após falha de rede, pois o servidor pode já tê-lo aceitado. Mostrar 413, 422 (string ou lista de detalhes), falha de rede, resposta inválida e erro inesperado em linguagem simples, usando conteúdo textual seguro.

Usar um único ciclo de consulta GET, cancelar ao sair/resetar e parar em COMPLETED/FAILED. Uma resposta antiga não pode substituir o job atual. Exibir o progresso informado, sem estimativa artificial e sem marcar sucesso antes de COMPLETED. Neste incremento já deve haver resultado ou erro final compreensível e download funcional; as tarefas seguintes enriquecem um fluxo operável.

Testar os controles reais no navegador, multipart recebido no servidor de teste, 202, processamento e terminal, falhas de envio, download e acessibilidade básica. Mocks de rede comprovam estados de UI; um pipeline controlado em servidor real comprova o contrato, sem chamar LLM nem baixar pesos.
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Os módulos de produção e teste web são criações propostas; somente os arquivos Python existentes citados no plano já foram verificados. Funções pytest, sem classes presumidas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/api/static/index.html; style.css; app.js | Estender shell com seleção, modos, presets, idioma, mensagens e resultado inicial. |
| Produção | src/video_subtitleler/api/static/form.js; api-client.js; job-monitor.js | Criar validação, FormData e consulta única com cancelamento e terminal. |
| Teste | tests/web/test_submit.py; tests/web/conftest.py | Criar testes de interação/contrato e ampliar fixture apenas para este ciclo. |
| Documentação | README.md; docs/web-interface/validation.md | Documentar geração, espera e download; registrar resultados. |

Atualizar esta tarefa e o [índice](index.md) no mesmo commit, preservando alterações alheias. Novos arquivos compartilhados têm proprietário inicial na seção 9 do plano.

## 4. Como implementar

1. Carregar ui-config e renderizar envio por seletor/arrastar, nome, tamanho, remoção, modos whisper_only/llm_hybrid e presets.
2. Validar MP4 não vazio e limite em bytes; validar idioma conforme schema real. Mostrar default sem fixar valores avançados de render.
3. Enviar nomes exatos de multipart e custom_style como string {}. Não escrever Content-Type; impedir duplo envio e repetição automática de POST.
4. Interpretar 202/UUID; mapear 413, 422, falha de rede e resposta malformada para mensagens seguras. Manter escolhas em caso de erro.
5. Implementar polling mínimo single-flight, token de geração/AbortController e término em COMPLETED/FAILED; mostrar status textual e download somente após conclusão.
6. Testar upload até download em browser com API controlada e servidor local; não consumir a assinatura LLM na suíte.

Manter predecessor utilizável. Para reverter, reverter primeiro consumidores posteriores que dependam deste comportamento. Não deixar código dependente de teste ou correção em tarefa futura.

## 5. Testes no mesmo commit

- MP4 com extensão maiúscula, arquivo vazio, limite exato e limite excedido; drop e seletor produzem o mesmo estado.
- Idioma auto/pt/en/es/manual válido e manual inválido; defaults whisper_only/movie_series.
- Verificar multipart real: custom_style é string JSON e não contém external_subtitle_file; um clique duplo não cria dois POSTs.
- Cobrir 202, QUEUED/PROCESSING/COMPLETED/FAILED, resposta inválida, rede e detalhes 422 em string/lista; sem POST automático após timeout.
- Verificar cancelamento do acompanhamento e proteção contra resposta antiga; link de download acessível apenas no sucesso.

Testes com API controlada comprovam frontend/contrato; não são prova de GPU, LLM externa ou transcrição real. Integrações reais devem ser registradas separadamente, sem credenciais ou dados privados nas evidências.

## 6. Validação

Executar da raiz, com ferramentas de W01 preparadas e `.tmp` existente. Para a suíte dirigida, Chromium e plugin devem estar instalados; skip não representa aceite.

```powershell
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
.\.venv\Scripts\python -m pytest tests/web/test_submit.py -q
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python scripts/verify_plan_excerpts.py docs/web-interface/tasks
```

Em testes somente de navegador, acrescentar `--browser chromium` se necessário. Servidor de teste em porta temporária, sem interromper a porta 8000 do usuário. W01 também executa `python -m build --outdir .tmp/web-dist` e verifica assets no wheel instalado fora do checkout. Comandos futuros não foram executados nesta decomposição.

## 7. Gates e fora do escopo

- API existente é precondição; mocks de estados não comprovam Whisper/LLM reais.
- Fora do escopo: arquivo externo, controles avançados, stepper completo e player. Download/status textual já devem funcionar neste commit.
- Preservar API/CLI, configuração CUDA/LLM e chaves locais; não publicar nem instalar ferramentas durante a fase documental.
- Documentação e snapshots de testes não substituem inspeção real quando esta for requerida.

## 8. Critérios de aceite (DoD)

- [ ] Um MP4 pode ser enviado nos dois modos iniciais, acompanhado até terminal e baixado; falhas são compreensíveis e não duplicam jobs.
- [ ] Testes automatizados positivos, negativos e regressões entregues no mesmo commit e aprovados; gates/ausências registrados.
- [ ] Documentação afetada, evidências desta tarefa e status do índice atualizados com resultados reais.
- [ ] Trecho literal validado por `verify_plan_excerpts.py`, links e critérios conferidos.
- [ ] Dependências, reversibilidade, acessibilidade aplicável e limites de escopo verificados sem mudanças alheias.
- [ ] Um único commit de implementação criado com a mensagem prevista e arquivos selecionados explicitamente.

---
## Status de implementação da tarefa

| Item | Status |
|---|---|
| Implementação | Não iniciada |
| Testes | Não iniciados |
| Documentação de implementação | Não iniciada |
| Validação do usuário | Pendente |

**Progresso geral:** 0%

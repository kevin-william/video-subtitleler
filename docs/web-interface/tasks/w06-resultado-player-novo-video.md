# W06 — Reproduzir o resultado e iniciar outro vídeo com estado limpo

> **Instruções do projeto:** manter o [contexto e convenções](index.md#contexto-e-convenções) e as instruções AGENTS fornecidas na sessão.

> **Status:** Não iniciada
> **Progresso:** 0%
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** A definir
> **Dependências:** [W05](w05-progresso-resiliente.md)
> **Commit único:** `feat(web): preview subtitle results and reset the workflow`

## 1. Por que

Completar a experiência de resultado com player e reutilização da interface. Testes de mídia, liberação de recursos e segundo ciclo acompanham o comportamento que introduzem.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trecho literal e contíguo da seção 8. Escolhas adicionais aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
## 8. W06 — Reprodução, download e reinício do fluxo

Em COMPLETED, apresentar player HTML5 com controles, link de download `.mp4` e “Processar novo vídeo”. Usar o endpoint real `/api/v1/jobs/{job_id}/download`; nunca renderizar HTML recebido como erro ou usar caminho local retornado pela API. Nenhum player deve aparecer em QUEUED/PROCESSING/FAILED.

Tratar erro de carregamento/reprodução com mensagem e manter o download como alternativa. Testar Content-Type `video/mp4`, Range/206 quando suportado pelo servidor e download completo; a resposta atual usa FileResponse e deve ser verificada antes de propor mudanças em headers/rotas. Alterar o backend somente se um teste reproduzir incompatibilidade com reprodução, mantendo o download existente.

“Processar novo vídeo” deve interromper acompanhamento, remover src e liberar objetos/timers, limpar arquivos, erros, job e customizações, restaurar padrões e devolver foco ao envio. Não apagar outputs do servidor nem cancelar processamento remoto. Não carregar todo o vídeo em base64 ou memória JavaScript para reproduzi-lo.

Finalizar responsividade nos painéis de resultado/erro em 360 px e 1280 px, navegação por teclado, contraste, foco, `aria-live`, `progressbar` e preferência por movimento reduzido. Esses requisitos já se aplicam aos componentes desde sua tarefa de origem; esta tarefa cobre o fluxo de resultado e sua composição, não posterga testes ou acessibilidade anteriores.

Testar navegador com vídeo real sintético H.264/AAC: metadados, reprodução quando o browser oferecer codec, seek, download, erro de mídia e segundo processamento sem estado residual. Registrar codec indisponível como gate e verificar ao menos em Chrome/Edge do Windows antes de declarar reprodução aprovada. Incluir regressão do ciclo completo local com FFmpeg e inspeção visual dos dois presets.
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Os módulos de produção e teste web são criações propostas; somente os arquivos Python existentes citados no plano já foram verificados. Funções pytest, sem classes presumidas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/api/static/index.html; style.css; app.js; job-monitor.js | Adicionar player, erro de mídia, download e reset completo do fluxo. |
| Produção condicional | src/video_subtitleler/api/routes.py | Alterar headers/streaming somente se teste demonstrar incompatibilidade; preservar rota de download. |
| Teste | tests/web/test_result.py; tests/web/conftest.py; tests/test_web_ui.py; tests/test_api.py | Criar teste de player real, Range/download e segundo ciclo; ampliar HTTP apenas se necessário. |
| Documentação | README.md; docs/web-interface/validation.md | Documentar operação final, codecs, resultados e inspeção visual. |

Atualizar esta tarefa e o [índice](index.md) no mesmo commit, preservando alterações alheias. Novos arquivos compartilhados têm proprietário inicial na seção 9 do plano.

## 4. Como implementar

1. Mostrar player/baixar somente em COMPLETED, usando URL do job; download deve funcionar mesmo com erro de codec/player.
2. Verificar FileResponse real, Content-Type, Range/206 e seek antes de alterar o backend; nunca baixar o MP4 inteiro para base64.
3. Implementar processar novo vídeo com descarte de recursos, src, timers, arquivos, overrides e job; retornar foco e defaults sem apagar dados remotos.
4. Testar resultado/erro em 360 e 1280 px, teclado, foco e anúncios acessíveis; não postergar correções anteriores de acessibilidade para esta tarefa.
5. Executar composição com FFmpeg local nos dois presets, verificar browser/codec e registrar o que foi inspecionado por humano.

Manter predecessor utilizável. Para reverter, reverter primeiro consumidores posteriores que dependam deste comportamento. Não deixar código dependente de teste ou correção em tarefa futura.

## 5. Testes no mesmo commit

- Sem player em estado não terminal ou FAILED; em COMPLETED src correto, metadados, play/seek quando codec disponível e botão baixar.
- Range/206 e conteúdo completo por HTTP real; arquivo ausente e erro do player mantêm alternativa de download com mensagem.
- Novo vídeo limpa estado e cancela acompanhamento anterior; segundo ciclo completo não reutiliza job/arquivo/customização.
- Layout em 360/1280 px sem overflow, foco por teclado, aria-live e movimento reduzido; registrar verificação em Chrome/Edge Windows.
- Regressão dos três modos e dois presets; separar rede mockada de integração real com FFmpeg e validação opcional Whisper/LLM.

Testes com API controlada comprovam frontend/contrato; não são prova de GPU, LLM externa ou transcrição real. Integrações reais devem ser registradas separadamente, sem credenciais ou dados privados nas evidências.

## 6. Validação

Executar da raiz, com ferramentas de W01 preparadas e `.tmp` existente. Para a suíte dirigida, Chromium e plugin devem estar instalados; skip não representa aceite.

```powershell
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
.\.venv\Scripts\python -m pytest tests/web/test_result.py tests/test_web_ui.py tests/test_api.py -q
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python scripts/verify_plan_excerpts.py docs/web-interface/tasks
```

Em testes somente de navegador, acrescentar `--browser chromium` se necessário. Servidor de teste em porta temporária, sem interromper a porta 8000 do usuário. W01 também executa `python -m build --outdir .tmp/web-dist` e verifica assets no wheel instalado fora do checkout. Comandos futuros não foram executados nesta decomposição.

## 7. Gates e fora do escopo

- Browser precisa suportar H.264/AAC para comprovar reprodução; registrar falta de codec como gate e validar em Chrome/Edge Windows.
- Fora do escopo: editor de legendas, histórico, exclusão de outputs, streaming dedicado e publicação remota.
- Preservar API/CLI, configuração CUDA/LLM e chaves locais; não publicar nem instalar ferramentas durante a fase documental.
- Documentação e snapshots de testes não substituem inspeção real quando esta for requerida.

## 8. Critérios de aceite (DoD)

- [ ] O vídeo concluído reproduz/permite download, erros de mídia são tratados e um segundo processamento começa limpo e acessível.
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

# W05 — Mostrar etapas e recuperar o acompanhamento interrompido

> **Instruções do projeto:** manter o [contexto e convenções](index.md#contexto-e-convenções) e as instruções AGENTS fornecidas na sessão.

> **Status:** Não iniciada
> **Progresso:** 0%
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** A definir
> **Dependências:** [W04](w04-estilo-avancado.md)
> **Commit único:** `feat(web): show pipeline steps and recover job polling`

## 1. Por que

Ampliar o acompanhamento já funcional com explicação das cinco etapas e recuperação de falhas de consulta sem criar outro processamento.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trecho literal e contíguo da seção 7. Escolhas adicionais aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
## 7. W05 — Etapas visuais e recuperação de consultas

Expandir o monitoramento textual com barra percentual acessível e cinco etapas: extração de áudio, transcrição, refinamento, geração da legenda e renderização. Renderizar PENDING, RUNNING, COMPLETED, SKIPPED e FAILED com texto/ícone, sem depender apenas de cor. QUEUED pode ter `current_step=null`; etapas dispensadas são um estado normal. Progresso enviado pelo backend é por etapas, não medição contínua do trabalho.

Consultar a cada 1.500 ms após a conclusão da consulta anterior, com AbortController e timeout de 10 s por consulta. Recuperar até três falhas transitórias de GET (rede/timeout/5xx) com esperas de 1,5 s, 3 s e 6 s; após a terceira tentativa de recuperação falhar, pausar e oferecer “Retomar acompanhamento” para o mesmo job. 404 deve encerrar a consulta com “Processamento não encontrado”; 422/JSON inválido deve pausar com erro de protocolo. Não transformar falha de consulta em FAILED de processamento.

Recuperação não cria outro job. Encerrar timers/requisições em terminal, reset ou descarte; resposta atrasada não reabre resultado antigo. A navegação/atualização da página não terá retomada persistente nesta versão; avisar antes de sair se houver acompanhamento ativo, sem prometer cancelar trabalho no servidor.

Testar sequências completas e saltos de etapas, SKIPPED em external/fallback, falha de job, rede intermitente, 404, timeout, recuperação manual, ausência de GET sobrepostos e descarte de respostas antigas. Usar relógio/rede controlados em vez de testes que aguardam longos tempos reais.
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Os módulos de produção e teste web são criações propostas; somente os arquivos Python existentes citados no plano já foram verificados. Funções pytest, sem classes presumidas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/api/static/job-monitor.js; api-client.js; index.html; style.css; app.js | Estender polling, stepper, retries limitados e retomada manual. |
| Teste | tests/web/test_progress.py; tests/web/test_submit.py | Criar testes de estados, rede, concorrência e regressão do fluxo inicial. |
| Documentação | README.md; docs/web-interface/validation.md | Explicar percentuais por etapa, SKIPPED e limites da retomada. |

Atualizar esta tarefa e o [índice](index.md) no mesmo commit, preservando alterações alheias. Novos arquivos compartilhados têm proprietário inicial na seção 9 do plano.

## 4. Como implementar

1. Renderizar as cinco etapas e todos os status com texto/ícone; não confundir refinamento dispensado com erro.
2. Manter single-flight e agendar após a resposta; aplicar timeout 10 s e três recuperações com esperas 1,5/3/6 s.
3. Separar falha transitória de consulta de FAILED do job; após esgotar tentativas oferecer retomar o mesmo UUID sem novo POST.
4. Tratar 404 como job não encontrado e 422/JSON inválido como protocolo; limpar timers/AbortController e descartar respostas antigas.
5. Avisar ao sair durante acompanhamento; não prometer retomada após reload nem cancelamento no servidor.

Manter predecessor utilizável. Para reverter, reverter primeiro consumidores posteriores que dependam deste comportamento. Não deixar código dependente de teste ou correção em tarefa futura.

## 5. Testes no mesmo commit

- QUEUED com current_step null, saltos de porcentagem/etapa, cinco estados, external e LLM SKIPPED, COMPLETED e FAILED.
- Rede/5xx/timeout com três recuperações, esgotamento e retomada manual no mesmo job; conferir intervalos com relógio controlado.
- 404 encerra, protocolo inválido pausa; um pedido de status lento não gera consultas simultâneas.
- Reset/descarte aborta consultas e resposta atrasada não muda job atual; status de erro não é inserido como HTML.

Testes com API controlada comprovam frontend/contrato; não são prova de GPU, LLM externa ou transcrição real. Integrações reais devem ser registradas separadamente, sem credenciais ou dados privados nas evidências.

## 6. Validação

Executar da raiz, com ferramentas de W01 preparadas e `.tmp` existente. Para a suíte dirigida, Chromium e plugin devem estar instalados; skip não representa aceite.

```powershell
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
.\.venv\Scripts\python -m pytest tests/web/test_progress.py tests/web/test_submit.py -q
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python scripts/verify_plan_excerpts.py docs/web-interface/tasks
```

Em testes somente de navegador, acrescentar `--browser chromium` se necessário. Servidor de teste em porta temporária, sem interromper a porta 8000 do usuário. W01 também executa `python -m build --outdir .tmp/web-dist` e verifica assets no wheel instalado fora do checkout. Comandos futuros não foram executados nesta decomposição.

## 7. Gates e fora do escopo

- Dados do backend podem saltar etapas entre consultas; não fabricar histórico observado nem estimativa contínua.
- Fora do escopo: WebSocket/SSE, cancelamento remoto, histórico, retomada durável após reinício ou retry automático de POST.
- Preservar API/CLI, configuração CUDA/LLM e chaves locais; não publicar nem instalar ferramentas durante a fase documental.
- Documentação e snapshots de testes não substituem inspeção real quando esta for requerida.

## 8. Critérios de aceite (DoD)

- [ ] Stepper reflete os estados reais, e falhas de consulta se recuperam ou pausam de modo seguro, sem duplicar jobs nem sobrepor requisições.
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

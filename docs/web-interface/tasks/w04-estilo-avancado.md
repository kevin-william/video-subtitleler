# W04 — Personalizar estilo preservando valores automáticos

> **Instruções do projeto:** manter o [contexto e convenções](index.md#contexto-e-convenções) e as instruções AGENTS fornecidas na sessão.

> **Status:** Não iniciada
> **Progresso:** 0%
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** A definir
> **Dependências:** [W03](w03-legendas-externas.md)
> **Commit único:** `feat(web): add validated subtitle style controls`

## 1. Por que

Entregar custom_style correto junto dos controles que o produzem. Valores visuais de exemplo não podem virar overrides silenciosos e alterar os presets.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trecho literal e contíguo da seção 6. Escolhas adicionais aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
## 6. W04 — Personalização avançada sem alterar automáticos

Adicionar painel expansível e ação “Restaurar estilo padrão”. Personalizações devem respeitar o contrato abaixo; campos não alterados ou restaurados são omitidos de `custom_style`, que é enviado como string JSON, nunca como objeto bruto ou `"undefined"`.

| Campo | Valores e comportamento |
|---|---|
| active_color / inactive_color | Hex `#RRGGBB`; cor nativa e texto sincronizados; exemplos Instagram `#00FFCC` / `#FFFFFF` |
| inactive_opacity | Número finito entre 0 e 1; referência visual 0,85 |
| font_size | Inteiro 8–200 ou automático; sugestões 36, 48 e 64 não são defaults do render |
| font_name | Texto 1–100 sem controles ASS; opções Arial, Impact, Trebuchet MS e Verdana não garantem fonte instalada |
| alignment | Inteiro 1–9 ou automático; grade visual 7/8/9 em cima, 4/5/6 no meio e 1/2/3 embaixo |
| margin_vertical | Inteiro 0–4096 ou automático; valor zero é válido |
| cpl | Inteiro 37–42; padrão 40 |

Manter visível a distinção entre automático e personalizado. Trocar preset preserva somente overrides explicitamente escolhidos e explica sua aplicação; não serializar os valores ilustrativos do preset como overrides automáticos. Cinema e Instagram resolvem tamanho de fonte e margem conforme resolução no backend.

Testar limites inclusivos, número vazio, NaN, decimais em inteiros, cores inválidas, sincronização de slider/campo e envio exato do JSON. Conferir aceitação pelo `CustomStyle` e regressões de W02/W03 no mesmo commit. Não simular preview de render como se fosse fiel ao FFmpeg.
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Os módulos de produção e teste web são criações propostas; somente os arquivos Python existentes citados no plano já foram verificados. Funções pytest, sem classes presumidas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/api/static/index.html; style.css; form.js; app.js | Estender accordion, controles sincronizados e serialização esparsa de overrides. |
| Teste | tests/web/test_style.py; tests/web/test_submit.py | Testar limites e payload no navegador com validação pelo contrato do backend. |
| Documentação | README.md; docs/web-interface/validation.md | Documentar automático/personalizado, restauração e fontes locais. |

Atualizar esta tarefa e o [índice](index.md) no mesmo commit, preservando alterações alheias. Novos arquivos compartilhados têm proprietário inicial na seção 9 do plano.

## 4. Como implementar

1. Implementar accordion com foco/aria-expanded e controles da tabela do plano; preservar navegação por teclado e movimento reduzido.
2. Separar valor ilustrativo de override explícito: campos automáticos são omitidos. Não fixar 36/48/64 como tamanho obrigatório.
3. Sincronizar cor/hex e sliders/números; validar valores finitos, tipos inteiros e zero legítimo antes de enviar.
4. Mapear grade ASS 7/8/9 no topo; restaurar padrão remove overrides, e troca de preset mantém apenas customizações explícitas.
5. Serializar JSON string com campos aceitos; conferir com CustomStyle real e manter resultados de W02/W03.

Manter predecessor utilizável. Para reverter, reverter primeiro consumidores posteriores que dependam deste comportamento. Não deixar código dependente de teste ou correção em tarefa futura.

## 5. Testes no mesmo commit

- Todos os limites inclusivos e um valor fora de cada faixa; decimal indevido em campos inteiros, campo vazio e NaN.
- Cores malformadas, nomes de fonte proibidos, zero na margem/opacidade, grade ASS e sincronização de pares de controle.
- Sem interação não há overrides involuntários; restaurar remove campos; trocar preset mantém somente campos escolhidos.
- Capturar FormData e validar JSON com CustomStyle; processamento controlado recebe o estilo escolhido.

Testes com API controlada comprovam frontend/contrato; não são prova de GPU, LLM externa ou transcrição real. Integrações reais devem ser registradas separadamente, sem credenciais ou dados privados nas evidências.

## 6. Validação

Executar da raiz, com ferramentas de W01 preparadas e `.tmp` existente. Para a suíte dirigida, Chromium e plugin devem estar instalados; skip não representa aceite.

```powershell
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
.\.venv\Scripts\python -m pytest tests/web/test_style.py tests/web/test_submit.py tests/web/test_external.py -q
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python scripts/verify_plan_excerpts.py docs/web-interface/tasks
```

Em testes somente de navegador, acrescentar `--browser chromium` se necessário. Servidor de teste em porta temporária, sem interromper a porta 8000 do usuário. W01 também executa `python -m build --outdir .tmp/web-dist` e verifica assets no wheel instalado fora do checkout. Comandos futuros não foram executados nesta decomposição.

## 7. Gates e fora do escopo

- Fontes listadas são sugestões, não detecção de instalação; render permanece responsabilidade do backend.
- Fora do escopo: preview que promete fidelidade ao FFmpeg, mudanças no schema de estilos ou defaults do ASSBuilder.
- Preservar API/CLI, configuração CUDA/LLM e chaves locais; não publicar nem instalar ferramentas durante a fase documental.
- Documentação e snapshots de testes não substituem inspeção real quando esta for requerida.

## 8. Critérios de aceite (DoD)

- [ ] Todos os controles respeitam CustomStyle e enviam somente overrides explícitos, sem destruir os padrões automáticos do backend.
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

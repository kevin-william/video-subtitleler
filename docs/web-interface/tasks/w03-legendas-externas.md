# W03 — Processar legendas externas com regras condicionais

> **Instruções do projeto:** manter o [contexto e convenções](index.md#contexto-e-convenções) e as instruções AGENTS fornecidas na sessão.

> **Status:** Concluída
> **Progresso:** 100%
> **Início:** 26/10/2026 | **Fim previsto:** - | **Fim real:** 26/10/2026
> **Responsável:** Codex
> **Dependências:** [W02](w02-envio-ciclo-inicial.md)
> **Commit único:** `feat(web): support external subtitle uploads`

## 1. Por que

Adicionar um terceiro fluxo completo, com regras de formato e tamanho que dependem de modo e preset. A validação do formulário e a integração external são inseparáveis nesta entrega.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trecho literal e contíguo da seção 5. Escolhas adicionais aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
## 5. W03 — Legenda externa com validação condicional

Acrescentar `external` e o campo `.srt`/`.vtt`/`.json`, exibido e obrigatório somente nesse modo. Ao sair de external, remover o campo do multipart e limpar estado/erros específicos. O limite deve considerar vídeo mais legenda, inclusive quando os dois arquivos individualmente cabem no limite.

Para `external` com `instagram_music`, aceitar apenas JSON e explicar que são necessárias palavras alinhadas; a extensão JSON não comprova alinhamento, que continuará sendo validado no backend. Cinema aceita SRT, VTT ou JSON. Arquivos vazios e extensão incorreta devem impedir o envio, mantendo as escolhas para correção.

Testar transições de modo/preset, soma dos tamanhos, troca de arquivo, nomes com espaços/acentos e omissão do arquivo em outros modos. Incluir integração local de navegador com pipeline real external/FFmpeg para cinema/SRT e Instagram/JSON; usar a fixture sintética do projeto e gerar arquivos temporários, sem depender de `output/demo` preexistente. Falta de FFmpeg deve ser gate explícito, não prova de sucesso.
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Os módulos de produção e teste web são criações propostas; somente os arquivos Python existentes citados no plano já foram verificados. Funções pytest, sem classes presumidas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/api/static/index.html; style.css; form.js; app.js | Estender modo external, validação conjunta e orientação de alinhamento. |
| Teste | tests/web/test_external.py; tests/web/conftest.py | Criar testes condicionais e mídia sintética temporária com FFmpeg. |
| Teste | tests/web/test_submit.py; tests/test_api.py | Executar regressões e ampliar apenas casos de contrato relacionados, se necessário. |
| Documentação | README.md; docs/web-interface/validation.md | Documentar SRT/VTT/JSON, soma dos limites e karaokê alinhado. |

Atualizar esta tarefa e o [índice](index.md) no mesmo commit, preservando alterações alheias. Novos arquivos compartilhados têm proprietário inicial na seção 9 do plano.

## 4. Como implementar

1. Revelar legenda obrigatória apenas em external; limpar erros/arquivo específico ao sair e omitir campo no multipart dos demais modos.
2. Aceitar SRT/VTT/JSON para cinema; em Instagram exigir JSON e informar que alinhamento será conferido pelo servidor.
3. Validar não vazio, extensão, soma vídeo+legenda segundo ui-config e combinações de preset sem interpretar JSON como prova de alinhamento.
4. Conservar arquivos/opções em 422 para permitir correção; toda saída de nome/erro deve ser texto seguro.
5. Reusar ciclo completo W02 e adicionar browser com backend real external/FFmpeg; gerar fixtures no diretório temporário.

Manter predecessor utilizável. Para reverter, reverter primeiro consumidores posteriores que dependam deste comportamento. Não deixar código dependente de teste ou correção em tarefa futura.

## 5. Testes no mesmo commit

- Trocar external para whisper/llm e voltar, alternar presets e substituir legenda; nenhum campo oculto indevido é enviado.
- Validar soma excedida mesmo quando cada arquivo cabe, arquivo vazio e extensão errada; testar limites inclusivos.
- Cinema SRT/VTT e Instagram JSON; rejeitar SRT com Instagram no frontend e JSON sem alinhamento no backend.
- Integração real local de cinema/SRT e Instagram/JSON até download; nomes com espaços/acentos e feedback de erro.

Testes com API controlada comprovam frontend/contrato; não são prova de GPU, LLM externa ou transcrição real. Integrações reais devem ser registradas separadamente, sem credenciais ou dados privados nas evidências.

## 6. Validação

Executar da raiz, com ferramentas de W01 preparadas e `.tmp` existente. Para a suíte dirigida, Chromium e plugin devem estar instalados; skip não representa aceite.

```powershell
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
.\.venv\Scripts\python -m pytest tests/web/test_external.py tests/web/test_submit.py tests/test_api.py -q
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python scripts/verify_plan_excerpts.py docs/web-interface/tasks
```

Em testes somente de navegador, acrescentar `--browser chromium` se necessário. Servidor de teste em porta temporária, sem interromper a porta 8000 do usuário. W01 também executa `python -m build --outdir .tmp/web-dist` e verifica assets no wheel instalado fora do checkout. Comandos futuros não foram executados nesta decomposição.

## 7. Gates e fora do escopo

- FFmpeg/FFprobe necessários à integração de mídia real; ausência gera pendência/skip explícito.
- Fora do escopo: gerar alinhamento para SRT, traduzir, editar legendas ou fabricar timestamps.
- Preservar API/CLI, configuração CUDA/LLM e chaves locais; não publicar nem instalar ferramentas durante a fase documental.
- Documentação e snapshots de testes não substituem inspeção real quando esta for requerida.

## 8. Critérios de aceite (DoD)

- [x] Os três modos respeitam arquivos condicionais, limite combinado e regras de karaokê; os dois fluxos external têm integração local verificada.
- [x] Testes automatizados positivos, negativos e regressões entregues no mesmo commit e aprovados; gates/ausências registrados.
- [x] Documentação afetada, evidências desta tarefa e status do índice atualizados com resultados reais.
- [x] Trecho literal validado por `verify_plan_excerpts.py`, links e critérios conferidos.
- [x] Dependências, reversibilidade, acessibilidade aplicável e limites de escopo verificados sem mudanças alheias.
- [x] Um único commit de implementação criado com a mensagem prevista e arquivos selecionados explicitamente.

---
## Status de implementação da tarefa

| Item | Status |
|---|---|
| Implementação | Concluída |
| Testes | Automatizados aprovados |
| Documentação de implementação | Atualizada |
| Validação do usuário | Pendente |

**Progresso geral:** 100%

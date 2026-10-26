# W01 — Servir a interface local e a configuração pública

> **Instruções do projeto:** manter o [contexto e convenções](index.md#contexto-e-convenções) e as instruções AGENTS fornecidas na sessão.

> **Status:** Concluída
> **Progresso:** 100%
> **Início:** 26/10/2026 | **Fim previsto:** - | **Fim real:** 26/10/2026
> **Responsável:** Codex
> **Dependências:** Nenhuma tarefa web; API existente é precondição.
> **Commit único:** `feat(web): serve local interface assets and public upload config`

## 1. Por que

Trocar a entrada técnica por uma página real e instalável, com configuração pública mínima. HTML, assets, empacotamento e testes do shell formam uma entrega utilizável sem alterar o processamento existente.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trecho literal e contíguo da seção 3. Escolhas adicionais aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
## 3. W01 — Página inicial, assets locais e configuração pública

Servir `index.html` em `/` com HTML 200, mantendo `/docs`, `/openapi.json` e as rotas de processamento. Montar somente `/static`, resolvida a partir de `__file__`, sem depender do diretório atual ou expor `.env`, `work/` e `output/`.

Criar shell acessível com título, texto explicativo, tema escuro, link secundário “Documentação da API” e estado real de conexão. GET `/api/v1/ui-config` deve responder apenas `{"max_upload_bytes": inteiro_positivo}` e não criar pipeline, banco, modelos ou diretórios; pode carregar `Settings` na primeira requisição, nunca no import. Uma resposta desse endpoint significa acesso à API, não comprova CUDA, LLM ou FFmpeg disponíveis. Falha de configuração deve produzir erro genérico, sem segredos, e estado visual de indisponibilidade.

Incluir os assets no pacote setuptools. Se o pacote estiver sem assets, falhar explicitamente no diagnóstico/instalação; não disfarçar a interface ausente redirecionando para Swagger. Com JavaScript indisponível, apresentar mensagem `noscript` e link técnico.

Testar a página e assets, MIME, configuração padrão/customizada, ausência de segredos/efeitos colaterais, preservação da API e conteúdo do wheel. Introduzir nessa mesma tarefa o extra de teste `web-test` com pytest-playwright/build, marcador `web_ui`, fixtures de servidor em porta temporária e desligamento garantido. O browser testa o shell real e a ausência de requisições a CDNs. Testes web sem ferramentas devem registrar skip explícito na suíte geral; na validação dirigida a instalação das ferramentas e do Chromium é obrigatória.
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Os módulos de produção e teste web são criações propostas; somente os arquivos Python existentes citados no plano já foram verificados. Funções pytest, sem classes presumidas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/api/app.py; src/video_subtitleler/api/ui.py | Modificar create_app; criar router de configuração sem Pipeline. |
| Produção | src/video_subtitleler/api/static/index.html; style.css; app.js | Criar shell acessível, estado de conexão e assets sem CDN obrigatório. |
| Ferramentas | pyproject.toml; requirements-web-test.lock | Declarar package-data, extra web-test, marcador web_ui e ferramentas compatíveis. |
| Teste | tests/test_web_ui.py; tests/test_api.py; tests/web/conftest.py; tests/web/test_shell.py | Criar cobertura HTTP/browser e atualizar test_root_opens_documentation para HTML 200. |
| Documentação | README.md; docs/web-interface/validation.md | Documentar acesso e criar registro honesto das verificações. |

Atualizar esta tarefa e o [índice](index.md) no mesmo commit, preservando alterações alheias. Novos arquivos compartilhados têm proprietário inicial na seção 9 do plano.

## 4. Como implementar

1. Resolver static a partir do módulo e montar /static sem capturar /docs ou /api/v1; não montar a raiz do repositório.
2. Criar shell sem botões ativos que prometam processamento ainda indisponível; manter link técnico e aviso noscript.
3. Criar GET /api/v1/ui-config com allowlist de max_upload_bytes; Settings lazy sem inicializar Pipeline, SQLite ou Whisper. Não devolver dump de Settings.
4. Declarar HTML/CSS/JS no setuptools; construir wheel e inspecionar seu conteúdo e uma instalação isolada fora da árvore de fontes.
5. Criar fixtures Playwright/Uvicorn em porta livre, testes locais sem .env pessoal e teardown garantido; fixar ferramentas validadas no lock.
6. Entregar testes do shell e de rede indisponível no mesmo commit; registrar os limites reais da validação.

Manter predecessor utilizável. Para reverter, reverter primeiro consumidores posteriores que dependam deste comportamento. Não deixar código dependente de teste ou correção em tarefa futura.

## 5. Testes no mesmo commit

- HTTP: / retorna HTML 200, /static/app.js e /static/style.css com tipos adequados; /docs e /openapi.json preservados; caminho estático inexistente 404.
- Configuração: limite padrão e customizado, somente campo permitido, sem chaves/caminhos e sem construção do pipeline ou criação de diretórios.
- Browser: shell renderiza sem CDN, teclado e foco acessíveis, conexão real/indisponível sem indicar GPU pronta.
- Pacote: wheel contém assets e funciona instalado fora do checkout; atualizar teste anterior de redirecionamento no mesmo commit.

Testes com API controlada comprovam frontend/contrato; não são prova de GPU, LLM externa ou transcrição real. Integrações reais devem ser registradas separadamente, sem credenciais ou dados privados nas evidências.

## 6. Validação

Executar da raiz, com ferramentas de W01 preparadas e `.tmp` existente. Para a suíte dirigida, Chromium e plugin devem estar instalados; skip não representa aceite.

```powershell
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
.\.venv\Scripts\python -m pytest tests/test_web_ui.py tests/test_api.py tests/web/test_shell.py -q
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python scripts/verify_plan_excerpts.py docs/web-interface/tasks
```

Em testes somente de navegador, acrescentar `--browser chromium` se necessário. Servidor de teste em porta temporária, sem interromper a porta 8000 do usuário. W01 também executa `python -m build --outdir .tmp/web-dist` e verifica assets no wheel instalado fora do checkout. Comandos futuros não foram executados nesta decomposição.

## 7. Gates e fora do escopo

- Instalar o extra web-test e Chromium durante a execução; versões e lock devem vir de resolução real.
- Fora do escopo: formulário de processamento e mudanças no pipeline; nenhuma tarefa futura é necessária para o shell funcionar.
- Preservar API/CLI, configuração CUDA/LLM e chaves locais; não publicar nem instalar ferramentas durante a fase documental.
- Documentação e snapshots de testes não substituem inspeção real quando esta for requerida.

## 8. Critérios de aceite (DoD)

- [x] Página HTML, assets e limite público funcionam no checkout e no pacote instalado, sem expor configurações privadas.
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

# Plano de implementação — Interface web do Video Subtitleler

Data: 26/10/2026. Status: implementado e validado; revisão humana pendente. Evidências em [validation.md](validation.md). Os fatos da seção 1 registram a base inspecionada antes da implementação.

## 1. Origem, objetivo e base verificada

Plano derivado da [referência preservada](reference/web_interface_plan.md), originalmente em `C:\Users\lord_\.gemini\antigravity\brain\bdf85ebf-40ae-48a5-b469-f571048b8524\web_interface_plan.md`. O documento externo é material de referência; suas notas de aprovação e exemplos não representam novas instruções do usuário nem código já implementado. A cópia local preserva o texto original.

Objetivo: entregar uma interface em português para enviar MP4, escolher processamento e estilo, acompanhar o job, assistir ao resultado e baixar o vídeo. O endereço `/` será a interface; `/docs` continuará sendo a documentação técnica da API.

Fatos conferidos no repositório:

- `src/video_subtitleler/api/app.py` contém `create_app` e a rota `/`, hoje um redirecionamento para `/docs`.
- `api/routes.py` oferece POST `/api/v1/subtitles/generate`, GET `/api/v1/jobs/{job_id}` e GET `/api/v1/jobs/{job_id}/download`.
- O POST usa multipart, responde 202 e executa o pipeline em background; o resultado não vem na resposta de envio.
- `models/schema.py` define os modos, presets, etapas, status, idioma e limites de `CustomStyle`. `services/ass_builder.py` resolve os valores automáticos por preset e resolução.
- `Settings.max_upload_bytes` vale 500.000.000 por padrão e o backend aplica esse limite à soma do vídeo e da legenda externa.
- Existem pytest, TestClient, fixtures de vídeo sintético e pipeline substituível em `tests/conftest.py`; não existem assets web nem suíte de navegador.
- O pacote usa setuptools e layout `src`; `pyproject.toml` ainda não declara os arquivos HTML/CSS/JS como dados de pacote.
- Há alterações locais anteriores em API, CUDA, LLM, testes e documentação. Preservá-las; este plano não autoriza implementá-las novamente, revertê-las ou incluí-las indiscriminadamente em commits.

## 2. Decisões e adaptações da referência

| Tema | Decisão para este plano | Relação com a referência |
|---|---|---|
| Hospedagem | FastAPI na mesma origem, `/` para HTML e `/static/` para assets | Mantido |
| Visual | Tema escuro, responsivo, legível, controles em português e contraste adequado | Mantido, com acessibilidade como requisito de cada entrega |
| Frontend | HTML semântico, CSS local e JavaScript nativo modular | Adaptação explícita: substitui Tailwind/Alpine via CDN por funcionamento sem internet e sem dependências de runtime externas |
| Build | Sem Node, npm, Vite, bundler ou servidor adicional | Mantido; Playwright Python é ferramenta de teste, não de runtime |
| Configuração pública | GET `/api/v1/ui-config`, retornando somente `max_upload_bytes` | Complemento para evitar limite fixo divergente do `.env` |
| Polling | Uma consulta de cada vez, próxima consulta 1.500 ms após a anterior terminar | Adaptação: evita sobreposição possível com `setInterval` |
| Estilo | Valores não personalizados são omitidos do JSON; backend resolve automáticos | Complemento para não fixar indevidamente tamanho/fonte/alinhamento de outro preset |
| Instalação | HTML, CSS, JS e eventuais ícones locais incluídos no wheel/sdist | Complemento necessário ao empacotamento existente |
| Testes | TestClient para HTTP e Playwright Python para comportamento visível | Amplia os testes de arquivos estáticos sugeridos na referência |

Nenhuma aprovação adicional é exigida apenas pela seção “User Review Required” da referência. As adaptações estão explícitas para revisão; não são apresentadas como preferências previamente confirmadas pelo usuário.

## 3. W01 — Página inicial, assets locais e configuração pública

Servir `index.html` em `/` com HTML 200, mantendo `/docs`, `/openapi.json` e as rotas de processamento. Montar somente `/static`, resolvida a partir de `__file__`, sem depender do diretório atual ou expor `.env`, `work/` e `output/`.

Criar shell acessível com título, texto explicativo, tema escuro, link secundário “Documentação da API” e estado real de conexão. GET `/api/v1/ui-config` deve responder apenas `{"max_upload_bytes": inteiro_positivo}` e não criar pipeline, banco, modelos ou diretórios; pode carregar `Settings` na primeira requisição, nunca no import. Uma resposta desse endpoint significa acesso à API, não comprova CUDA, LLM ou FFmpeg disponíveis. Falha de configuração deve produzir erro genérico, sem segredos, e estado visual de indisponibilidade.

Incluir os assets no pacote setuptools. Se o pacote estiver sem assets, falhar explicitamente no diagnóstico/instalação; não disfarçar a interface ausente redirecionando para Swagger. Com JavaScript indisponível, apresentar mensagem `noscript` e link técnico.

Testar a página e assets, MIME, configuração padrão/customizada, ausência de segredos/efeitos colaterais, preservação da API e conteúdo do wheel. Introduzir nessa mesma tarefa o extra de teste `web-test` com pytest-playwright/build, marcador `web_ui`, fixtures de servidor em porta temporária e desligamento garantido. O browser testa o shell real e a ausência de requisições a CDNs. Testes web sem ferramentas devem registrar skip explícito na suíte geral; na validação dirigida a instalação das ferramentas e do Chromium é obrigatória.

## 4. W02 — Primeiro ciclo utilizável com Whisper e LLM

Entregar um fluxo completo inicial: selecionar/arrastar um MP4, escolher `whisper_only` ou `llm_hybrid`, escolher `movie_series` ou `instagram_music`, enviar, acompanhar status textual e obter um link de download quando concluído. Padrões: `whisper_only`, `movie_series`, idioma `auto`. Oferecer `pt`, `en`, `es` e código manual minúsculo de 2–3 letras, conforme o contrato real, sem prometer validação do catálogo ISO.

Validar extensão `.mp4` sem diferenciar maiúsculas, arquivo não vazio e tamanho em bytes segundo `ui-config`; MIME do navegador é apenas indicativo. Mostrar nome, tamanho e remoção do arquivo. Drag-and-drop deve ter alternativa por teclado. Se a configuração pública não puder ser obtida, bloquear novo envio com explicação e ação para tentar novamente.

Montar `FormData` com os nomes reais da API; `custom_style` será inicialmente `"{}"`. Não definir manualmente o Content-Type multipart. Bloquear duplo envio, validar 202 e UUID recebido e consultar apenas o job aceito; nunca repetir POST automaticamente após falha de rede, pois o servidor pode já tê-lo aceitado. Mostrar 413, 422 (string ou lista de detalhes), falha de rede, resposta inválida e erro inesperado em linguagem simples, usando conteúdo textual seguro.

Usar um único ciclo de consulta GET, cancelar ao sair/resetar e parar em COMPLETED/FAILED. Uma resposta antiga não pode substituir o job atual. Exibir o progresso informado, sem estimativa artificial e sem marcar sucesso antes de COMPLETED. Neste incremento já deve haver resultado ou erro final compreensível e download funcional; as tarefas seguintes enriquecem um fluxo operável.

Testar os controles reais no navegador, multipart recebido no servidor de teste, 202, processamento e terminal, falhas de envio, download e acessibilidade básica. Mocks de rede comprovam estados de UI; um pipeline controlado em servidor real comprova o contrato, sem chamar LLM nem baixar pesos.

## 5. W03 — Legenda externa com validação condicional

Acrescentar `external` e o campo `.srt`/`.vtt`/`.json`, exibido e obrigatório somente nesse modo. Ao sair de external, remover o campo do multipart e limpar estado/erros específicos. O limite deve considerar vídeo mais legenda, inclusive quando os dois arquivos individualmente cabem no limite.

Para `external` com `instagram_music`, aceitar apenas JSON e explicar que são necessárias palavras alinhadas; a extensão JSON não comprova alinhamento, que continuará sendo validado no backend. Cinema aceita SRT, VTT ou JSON. Arquivos vazios e extensão incorreta devem impedir o envio, mantendo as escolhas para correção.

Testar transições de modo/preset, soma dos tamanhos, troca de arquivo, nomes com espaços/acentos e omissão do arquivo em outros modos. Incluir integração local de navegador com pipeline real external/FFmpeg para cinema/SRT e Instagram/JSON; usar a fixture sintética do projeto e gerar arquivos temporários, sem depender de `output/demo` preexistente. Falta de FFmpeg deve ser gate explícito, não prova de sucesso.

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

## 7. W05 — Etapas visuais e recuperação de consultas

Expandir o monitoramento textual com barra percentual acessível e cinco etapas: extração de áudio, transcrição, refinamento, geração da legenda e renderização. Renderizar PENDING, RUNNING, COMPLETED, SKIPPED e FAILED com texto/ícone, sem depender apenas de cor. QUEUED pode ter `current_step=null`; etapas dispensadas são um estado normal. Progresso enviado pelo backend é por etapas, não medição contínua do trabalho.

Consultar a cada 1.500 ms após a conclusão da consulta anterior, com AbortController e timeout de 10 s por consulta. Recuperar até três falhas transitórias de GET (rede/timeout/5xx) com esperas de 1,5 s, 3 s e 6 s; após a terceira tentativa de recuperação falhar, pausar e oferecer “Retomar acompanhamento” para o mesmo job. 404 deve encerrar a consulta com “Processamento não encontrado”; 422/JSON inválido deve pausar com erro de protocolo. Não transformar falha de consulta em FAILED de processamento.

Recuperação não cria outro job. Encerrar timers/requisições em terminal, reset ou descarte; resposta atrasada não reabre resultado antigo. A navegação/atualização da página não terá retomada persistente nesta versão; avisar antes de sair se houver acompanhamento ativo, sem prometer cancelar trabalho no servidor.

Testar sequências completas e saltos de etapas, SKIPPED em external/fallback, falha de job, rede intermitente, 404, timeout, recuperação manual, ausência de GET sobrepostos e descarte de respostas antigas. Usar relógio/rede controlados em vez de testes que aguardam longos tempos reais.

## 8. W06 — Reprodução, download e reinício do fluxo

Em COMPLETED, apresentar player HTML5 com controles, link de download `.mp4` e “Processar novo vídeo”. Usar o endpoint real `/api/v1/jobs/{job_id}/download`; nunca renderizar HTML recebido como erro ou usar caminho local retornado pela API. Nenhum player deve aparecer em QUEUED/PROCESSING/FAILED.

Tratar erro de carregamento/reprodução com mensagem e manter o download como alternativa. Testar Content-Type `video/mp4`, Range/206 quando suportado pelo servidor e download completo; a resposta atual usa FileResponse e deve ser verificada antes de propor mudanças em headers/rotas. Alterar o backend somente se um teste reproduzir incompatibilidade com reprodução, mantendo o download existente.

“Processar novo vídeo” deve interromper acompanhamento, remover src e liberar objetos/timers, limpar arquivos, erros, job e customizações, restaurar padrões e devolver foco ao envio. Não apagar outputs do servidor nem cancelar processamento remoto. Não carregar todo o vídeo em base64 ou memória JavaScript para reproduzi-lo.

Finalizar responsividade nos painéis de resultado/erro em 360 px e 1280 px, navegação por teclado, contraste, foco, `aria-live`, `progressbar` e preferência por movimento reduzido. Esses requisitos já se aplicam aos componentes desde sua tarefa de origem; esta tarefa cobre o fluxo de resultado e sua composição, não posterga testes ou acessibilidade anteriores.

Testar navegador com vídeo real sintético H.264/AAC: metadados, reprodução quando o browser oferecer codec, seek, download, erro de mídia e segundo processamento sem estado residual. Registrar codec indisponível como gate e verificar ao menos em Chrome/Edge do Windows antes de declarar reprodução aprovada. Incluir regressão do ciclo completo local com FFmpeg e inspeção visual dos dois presets.

## 9. Organização proposta de arquivos e propriedade

Todos os caminhos abaixo são relativos à raiz do repositório. Arquivos novos são propostas, não implementação existente. A primeira tarefa listada cria o arquivo; as demais o estendem em seu próprio comportamento.

| Arquivo/grupo | Proprietário inicial | Extensões |
|---|---|---|
| src/video_subtitleler/api/app.py | W01 | W06 somente se teste de mídia exigir |
| src/video_subtitleler/api/ui.py (novo router/config pública) | W01 | — |
| src/video_subtitleler/api/static/index.html, style.css, app.js | W01 | W02–W06 nos componentes respectivos |
| src/video_subtitleler/api/static/api-client.js, job-monitor.js | W02 | W05; W06 para liberação de recursos |
| src/video_subtitleler/api/static/form.js | W02 | W03 e W04 |
| tests/test_web_ui.py | W01 | W06 apenas se houver mudança HTTP de mídia |
| tests/web/conftest.py e test_shell.py | W01 | Fixture ampliada apenas junto do comportamento que a utiliza |
| tests/web/test_submit.py | W02 | W03/W04/W05 em regressões relacionadas |
| tests/web/test_external.py | W03 | — |
| tests/web/test_style.py | W04 | — |
| tests/web/test_progress.py | W05 | — |
| tests/web/test_result.py | W06 | — |
| tests/test_api.py | W01 troca a expectativa do redirect | W03/W06 se contratos existentes forem exercitados |
| src/video_subtitleler/services/llm_enhancer.py; tests/test_llm_enhancer.py | W06, correção necessária descoberta na integração real | Isolar/fechar transportes por refinamento e regredir duas chamadas persistentes consecutivas |
| pyproject.toml, requirements-web-test.lock (novo) | W01 | Atualizar apenas se uma tarefa introduzir dependência justificada |
| README.md e docs/web-interface/validation.md (novo registro na execução) | W01 | Cada tarefa registra seu comportamento e evidências |

## 10. Ordem, atomicidade e validação

São seis tarefas, seis commits de implementação e 36 critérios de aceite. Sequência oficial no [índice de tarefas](tasks/index.md): W01 → W02 → W03 → W04 → W05 → W06. Cada commit entrega código, seus testes, documentação afetada e progresso. Não criar commit posterior somente para testar código anterior. A reversão de uma tarefa preserva predecessoras; reverter consumidores posteriores primeiro.

Instalação de ferramentas, a executar somente durante a implementação de W01:

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev,api,web-test]"
.\.venv\Scripts\python -m playwright install chromium
```

O extra `web-test`, os módulos `tests/web` e o lock correspondente ainda serão criados em W01. Escolher e registrar versões compatíveis no ambiente real nessa tarefa; não há versões instaladas presumidas por este plano.

Comandos previstos após as respectivas tarefas:

```powershell
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
.\.venv\Scripts\python -m pytest tests/test_web_ui.py tests/test_api.py -q
.\.venv\Scripts\python -m pytest tests/web -m web_ui --browser chromium -q
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m build --outdir .tmp/web-dist
.\.venv\Scripts\python -m uvicorn video_subtitleler.api.app:app --host 127.0.0.1 --port 8000
```

Criar `.tmp` se necessário. O servidor manual bloqueia até Ctrl+C e não conta como teste automatizado. Testes web iniciam servidor próprio em porta livre, diretório temporário e configuração isolada; não derrubam o serviço pessoal da porta 8000 e não usam a chave LLM do `.env`. Downloads de ferramentas/browser exigem rede na preparação; a interface em runtime não exige CDN.

Teste padrão de navegador deve usar API controlada e não chamar provedores nem baixar modelos. Integração com FFmpeg prova mídia; testes opcionais com pesos locais e voz autorizada provam Whisper. Teste LLM externo só com autorização aplicável e registro separado de consumo, sem segredos em evidências. Não declarar teste mockado como validação real de GPU/LLM/voz.

## 11. Gates, limites e fora do escopo

- Infra de testes: Python do projeto, dependências de teste e navegador; no Windows, permitir comunicação HTTP local para TestClient/Uvicorn/Playwright. Falhas de infraestrutura são pendências explícitas.
- Mídia real: FFmpeg/FFprobe com codecs necessários e fonte disponível. GPU e LLM continuam configuradas no servidor, não são selecionadas ou expostas pelo frontend.
- Reprodução real depende do suporte de codec do navegador; download não substitui prova de reprodução.
- A aplicação permanece local em 127.0.0.1. Sem autenticação, publicação, acesso remoto, CORS permissivo, histórico/listagem de jobs, tradução, editor de legendas, cancelamento de servidor, retomada durável, WebSocket/SSE ou fila distribuída.
- Não criar endpoints que retornem chaves, caminhos de modelos, database_path ou dump de Settings. Nomes de arquivo e erros entram no DOM com `textContent` ou equivalente seguro.
- Arquivos do plano são documentação; status inicial é 0%. A criação deste pacote não executa implementação, testes de produção ou commits das tarefas.

## 12. Rastreabilidade e referências técnicas

| Referência original | Cobertura neste plano |
|---|---|
| Objetivos, Header e Backend/Assets | W01, W02 |
| Upload e configurações principais | W02, W03 |
| custom_style | W04 |
| Polling e stepper | W02 básico, W05 completo |
| Resultado e player | W02 download inicial, W06 player e reset |
| Testes automatizados e integração manual | Testes junto de cada W01–W06 |
| Tailwind/Alpine via CDN | Adaptado na seção 2 para CSS/JS locais |

Documentação oficial consultada em 26/10/2026: [StaticFiles no FastAPI](https://fastapi.tiangolo.com/tutorial/static-files/), [dados de pacote setuptools](https://setuptools.pypa.io/en/latest/userguide/datafiles.html) e [Playwright Python com pytest](https://playwright.dev/python/docs/intro). São referências técnicas; a evidência de funcionamento virá da execução das tarefas.

## 13. Ajuste comprovado durante a execução

W06 incluiu uma correção de backend necessária ao segundo processamento híbrido: o cliente HTTP assíncrono era reutilizado depois que asyncio.run encerrava seu loop. A reprodução real mostrou primeira chamada aprovada e segunda com “Event loop is closed”. Cada refinamento agora possui transportes SDK próprios, encerrados dentro do loop; o teste local HTTP/1.1 cobre duas chamadas consecutivas e os dois presets foram verificados com MiniMax real. Isso não altera modelo, chave, prompt, timestamps nem política de fallback.

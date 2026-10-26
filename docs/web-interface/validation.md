# Validação da interface web — 26/10/2026

## W01 — Entrada e configuração

- HTTP/API: 17 testes aprovados; página inicial HTML, assets, preservação da API e allowlist de configuração.
- Navegador Chromium: shell local, layout 360 px e recuperação de configuração indisponível.
- Wheel e sdist construídos; assets HTML/CSS/JS presentes. Wheel instalado em `.tmp/web-installed`, importado fora da árvore de fontes e servido com TestClient.
- Dependências web registradas em `requirements-web-test.lock`. Sem dependência de CDN na interface.

Os testes usam Settings isolado e não acessam a chave LLM pessoal. A revisão humana continua pendente.

## W02 — Envio e ciclo inicial

13 testes de navegador aprovados (incluindo shell): multipart, servidor real com pipeline controlado, download, idioma, limites inclusivos, drop, 413/422/500, falha de rede e erro de job com conteúdo textual seguro. Nenhuma chamada LLM externa nestes testes.

## W03 — Legendas externas

16 testes de navegador aprovados (external e regressão de envio). Cinema com SRT e Instagram com JSON foram processados pelo backend real com FFmpeg e baixados. Validados: limite combinado, troca de modo, campos omitidos e rejeição de JSON sem palavras alinhadas pelo backend.

## W04 — Estilo avançado

23 testes de navegador aprovados (estilo e regressões de envio/external); 7 testes dirigidos repetidos após ajuste dos exemplos de cor automática. JSON verificado com CustomStyle: limites inclusivos, margem/opacidade zero, inteiros, cores, fonte, grade ASS, sincronização e restauração. Campos automáticos não viram overrides.

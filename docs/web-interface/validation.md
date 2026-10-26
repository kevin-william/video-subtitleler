# Validação da interface web — 26/10/2026

## W01 — Entrada e configuração

- HTTP/API: 17 testes aprovados; página inicial HTML, assets, preservação da API e allowlist de configuração.
- Navegador Chromium: shell local, layout 360 px e recuperação de configuração indisponível.
- Wheel e sdist construídos; assets HTML/CSS/JS presentes. Wheel instalado em `.tmp/web-installed`, importado fora da árvore de fontes e servido com TestClient.
- Dependências web registradas em `requirements-web-test.lock`. Sem dependência de CDN na interface.

Os testes usam Settings isolado e não acessam a chave LLM pessoal. A revisão humana continua pendente.

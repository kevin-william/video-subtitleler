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

## W05 — Etapas e recuperação de consultas

34 testes de navegador aprovados. Relógio controlado validou polling sem sobreposição, timeout de 10 s, três recuperações, pausa e retomada do mesmo UUID sem outro POST, 404, protocolo inválido, respostas antigas e término de consultas. Stepper cobre etapas dispensadas e barra usa percentuais reais.

## W06 — Player, novo vídeo e integração final

- Reprodução, seek, Content-Type video/mp4, Range/206 e download completo aprovados com vídeos H.264/AAC reais dos dois estilos. Nenhuma alteração foi necessária em FileResponse/rota de download.
- Testes dirigidos iniciais de resultado/API: 23 aprovados. Testes de resultado no Edge instalado: 6 aprovados. Layout 360/1280 px, foco, movimento reduzido, erro de mídia e segundo ciclo limpo verificados.
- A integração real descobriu um defeito anterior do backend: o SDK reutilizava transporte assíncrono entre chamadas asyncio.run e a segunda falhava com Event loop is closed. Corrigido com transportes SDK próprios por refinamento e fechamento dentro do loop; regressão HTTP/1.1 executa duas chamadas seguidas. As alterações anteriores de provedor/modelo foram preservadas e não incorporadas indiscriminadamente ao commit web.
- Edge com serviço real, voz sintética, Whisper/CUDA e MiniMax: Cinema COMPLETED em 14,72 s, LLM COMPLETED, download 87.714 bytes; Instagram COMPLETED em 5,44 s, LLM COMPLETED, download 114.844 bytes. Ambos reproduzidos e avançados no player, sem erros JavaScript. Artefatos em output/web-validation/20261026-182155/ e output/web-validation/20261026-182211/.
- O fallback também foi observado antes da correção e agora é explicado na área de resultado. Capturas desktop/mobile em .tmp/web-qa/ foram inspecionadas visualmente pelo agente; aprovação humana permanece pendente.
- Suíte final: **193 passed**, sem skips, em 39,89 s; inclui Whisper small real em CUDA/float16. pip check sem conflitos. Wheel e sdist finais construídos, seis assets conferidos e servidos a partir de instalação fora da árvore de fontes.
- Serviço principal reiniciado sem jobs ativos e verificado em http://127.0.0.1:8000/: raiz, JavaScript, configuração pública, Swagger e OpenAPI respondem 200. Prévia temporária da porta 8765 encerrada.

## Limites da entrega

Sem autenticação, acesso remoto, cancelamento de job, persistência do acompanhamento após reload, histórico ou editor de legendas. A reprodução depende de codec do navegador; o download permanece disponível. Falhas de provedor mantêm o fallback e aviso. Chaves não são enviadas ao browser e a suite padrão não chama provedores externos. O serviço local da porta 8000 foi deixado em execução para o usuário.

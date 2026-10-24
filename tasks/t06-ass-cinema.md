# T06 — Gerar ASS legível para cinema e séries

> **Instruções do projeto:** consultar [contexto e convenções](index.md#contexto-e-convenções) e preservar as instruções AGENTS fornecidas na sessão.

> **Status:** Concluída; gates externos documentados
> **Progresso:** 100%
> **Início:** 24/10/2026 | **Fim previsto:** - | **Fim real:** 24/10/2026
> **Responsável:** Codex
> **Dependências:** [T01](t01-base-contratos-configuracao.md)
> **Commit único:** `feat(ass): generate movie and series subtitles`

## 1. Por que

Entregar um gerador ASS válido e independente do motor de vídeo, com limites de legibilidade verificáveis.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trechos literais; escolhas e complementos de implementação aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
### A. Modo Cinema e Séries (`movie_series`)
* **Posicionamento**: Terço inferior centralizado (`Alignment = 2`).
* **Tipografia**: Fontes neutras e altamente legíveis (ex.: Roboto, Arial, Montserrat, Inter).
* **Padrão de Quebra**: Máximo de 37 a 42 caracteres por linha (CPL) e no máximo 2 linhas simultâneas.
* **Aspecto Visual**: Texto branco ou amarelo-clássico com contorno preto nítido de 2px e leve sombra para garantir legibilidade sobre qualquer fundo de cena.
* **Transição**: Exibição em bloco contínuo por sentença/fração de diálogo.
````
<!-- PLAN_EXCERPT_END -->

<!-- PLAN_EXCERPT_START -->
````text
## 7. Plano de Verificação

### Testes Automatizados
* **`tests/test_ass_builder.py`**:
  * Verifica se o arquivo `.ass` gerado contém os cabeçalhos corretos (`[V4+ Styles]` e `[Events]`).
  * Valida que o estilo `instagram_music` inclui as tags de tempo e destaque de palavras.
  * Valida que o estilo `movie_series` respeita as quebras de linha padrão.
* **`tests/test_llm_enhancer.py`**:
  * Testa o fluxo de enriquecimento com mock da API.
  * Testa o mecanismo de fallback quando a LLM gera exceção ou timeout.
* **`tests/test_api.py`**:
  * Testa o ciclo de vida dos jobs via TestClient do FastAPI.

### Verificação Manual
1. Gerar um vídeo curto de teste `.mp4` sintético via FFmpeg com áudio de voz.
2. Executar via CLI nos dois modos:
   - `python -m video_subtitleler.cli process video_teste.mp4 --style movie_series`
   - `python -m video_subtitleler.cli process video_teste.mp4 --style instagram_music`
3. Iniciar o servidor FastAPI (`uvicorn video_subtitleler.api.app:app`) e testar via Swagger UI (`/docs`).
4. Inspecionar o vídeo resultante em player para confirmar sincronismo e fidelidade visual.
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Todos os arquivos de produção/teste abaixo são criações propostas ou extensões de tarefas predecessoras, pois ainda não existem no repositório. Nomes de testes são módulos pytest propostos, não classes existentes verificadas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/services/ass_builder.py | Criar estrutura ASS e preset movie_series |
| Teste | tests/test_ass_builder.py | Criar casos de cinema e sintaxe ASS |
| Documentação | README.md | Documentar preset cinema, CPL e overrides |

Atualizar o status desta tarefa e o [índice](index.md) no mesmo commit de entrega.

## 4. Como implementar

1. Gerar Script Info com resolução fornecida pelo chamador, V4+ Styles e Events; converter segundos para centésimos e cores RGB para BGR ASS de forma determinística.
2. Aplicar Alignment=2, cor branca padrão com opção amarela, contorno 2px e sombra leve. Escolher fonte configurável disponível; não prometer fonte instalada sem verificar.
3. Usar CPL padrão 40 (configuração limitada a 37–42) e até duas linhas por evento. Dividir textos longos sem cortar palavras; para palavra isolada maior que CPL, definir quebra segura documentada e testada.
4. Quando houver palavras, usar seus limites para redistribuir eventos; quando só houver segmentos externos, distribuir intervalos de forma explícita para leitura em blocos sem alegar sincronismo por palavra. Nunca gerar evento de duração zero após arredondamento.
5. Escapar texto literal que possa ser interpretado como tags ASS e validar overrides. Não permitir que texto de usuário injete comandos de estilo.

Manter o pacote importável e os predecessores funcionando ao concluir. A reversão deste commit deve preservar os predecessores; reverter consumidores posteriores primeiro, se já existirem.

## 5. Testes no mesmo commit

- Verificar cabeçalhos, campos, alinhamento, cores BGR e tempos.
- Cobrir texto curto/longo, palavras extensas, Unicode, no máximo duas linhas e CPL configurado.
- Cobrir chaves, barras, quebras literais, tempos muito curtos e trilha vazia, com política documentada.

Código e testes são inseparáveis nesta tarefa. Testes unitários usam doubles nos limites externos; integrações reais são identificadas e relatadas separadamente, com skips explícitos quando seus recursos não existirem.

## 6. Validação

Executar da raiz após instalar o projeto com `python -m pip install -e ".[dev]"` (a instalação é entregue em T01):

```powershell
python -m pytest tests/test_ass_builder.py
python -m pytest tests/test_models.py
python scripts/verify_plan_excerpts.py tasks
```

Relatar comandos executados, resultados e gates pendentes. Servidor manual não conta como teste automatizado aprovado.

## 7. Gates e fora do escopo

- Fontes reais e legibilidade no vídeo dependem da validação com renderização posterior.
- Fora do escopo: efeito karaokê e execução de FFmpeg.
- Implementar apenas o comportamento desta tarefa; não antecipar consumidores das tarefas seguintes.
- A documentação de tarefas não comprova implementação ou execução dos testes de produção.

## 8. Critérios de aceite (DoD)

- [x] Comportamento de produção descrito implementado e importável.
- [x] Testes automatizados desta tarefa entregues no mesmo commit e aprovados; skips/gates relatados.
- [x] Documentação diretamente afetada atualizada.
- [x] Trechos literais validados por `scripts/verify_plan_excerpts.py`.
- [x] Dependências, limites de escopo e regressões dos predecessores conferidos.
- [x] Um único commit criado com a mensagem prevista, com status desta tarefa e índice atualizados.

---
## Status de implementação da tarefa

| Item | Status |
|---|---|
| Implementação | Concluída |
| Testes | Automatizados aprovados; gates relatados |
| Documentação de implementação | README e contratos atualizados |
| Validação do usuário | Pendente |

**Progresso geral:** 100%

## Registro de execução — 24/10/2026

Implementação e testes entregues no mesmo commit previsto. O snapshot isolado deste commit foi validado com `python -m pytest -q tests/test_ass_builder.py` antes do registro. Referências literais e links permanecem válidos.

Cabeçalhos ASS, CPL, duas linhas, escapes, palavras longas e tempos foram testados. Cinema foi validado sem depender do preset posterior.

Validação humana em player e uso com provedor LLM externo continuam pendentes conforme os gates do índice; não foram apresentados como aprovação automática.


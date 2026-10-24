# T07 — Adicionar karaokê com destaque exclusivo da palavra ativa

> **Instruções do projeto:** consultar [contexto e convenções](index.md#contexto-e-convenções) e preservar as instruções AGENTS fornecidas na sessão.

> **Status:** Concluída; gates externos documentados
> **Progresso:** 100%
> **Início:** 24/10/2026 | **Fim previsto:** - | **Fim real:** 24/10/2026
> **Responsável:** Codex
> **Dependências:** [T06](t06-ass-cinema.md)
> **Commit único:** `feat(ass): highlight active words in karaoke subtitles`

## 1. Por que

Acrescentar o segundo comportamento visual com testes no mesmo commit, preservando o preset cinema já entregue.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trechos literais; escolhas e complementos de implementação aparecem fora dos marcadores.

<!-- PLAN_EXCERPT_START -->
````text
### B. Modo Instagram e Música (`instagram_music`)
* **Posicionamento**: Terço médio/centro da tela (`Alignment = 5` ou `2` com margem vertical elevada).
* **Tipografia**: Fontes pesadas de alto impacto (ex.: Impact, Montserrat Black, The Bold Font).
* **Padrão de Quebra**: Frases curtas e rítmicas de 2 a 5 palavras por vez na tela.
* **Efeito Karaokê (Palavra Ativa)**:
  * As palavras do bloco atual aparecem na tela;
  * À medida que o cantor/locutor fala, a **palavra ativa muda para a cor de destaque** (ex.: `#00FFCC` ciano, `#FFD700` amarelo ouro ou `#FF1493` rosa choque);
  * As palavras inativas permanecem em cor neutra (branco com leve transparência).
* **Customizações**: Override via API/CLI de cor ativa, cor inativa, tamanho da fonte e alinhamento vertical.

---
````
<!-- PLAN_EXCERPT_END -->

<!-- PLAN_EXCERPT_START -->
````text
## 6. Configuração do LangChain (OpenCode Go / DeepSeek)

```python
# Exemplo de configuração flexível no src/video_subtitleler/services/llm_enhancer.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

class LLMEnhancer:
    def __init__(self, api_key: str, base_url: str = "https://api.opencode.ai/v1", model: str = "deepseek-chat"):
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.2,
            timeout=30.0
        )
```

O prompt envia as palavras extraídas com seus timestamps brutos e instrui o modelo a:
1. Corrigir ortografia e pontuação sem alterar tempos de início e fim.
2. Agrupar em segmentos conforme o estilo:
   - Para `instagram_music`: agrupar de 2 a 4 palavras com alta musicalidade e ritmo.
   - Para `movie_series`: criar frases completas de até 40 caracteres por linha.
3. Se a chamada à LLM falhar (rede, quota, timeout), o método `enhance_with_fallback()` loga o aviso e devolve o alinhamento nativo do Whisper imediatamente.

---
````
<!-- PLAN_EXCERPT_END -->

## 3. Onde implementar

Caminhos relativos à raiz. Todos os arquivos de produção/teste abaixo são criações propostas ou extensões de tarefas predecessoras, pois ainda não existem no repositório. Nomes de testes são módulos pytest propostos, não classes existentes verificadas.

| Tipo | Arquivo | Ação |
|---|---|---|
| Produção | src/video_subtitleler/services/ass_builder.py | Adicionar preset instagram_music |
| Teste | tests/test_ass_builder.py | Adicionar casos de karaokê e regressões de cinema |
| Documentação | README.md | Documentar grupos, cores e exigência de palavras |

Atualizar o status desta tarefa e o [índice](index.md) no mesmo commit de entrega.

## 4. Como implementar

1. Agrupar 2–5 palavras no caminho determinístico, respeitando os grupos válidos de 2–4 vindos da LLM; aceitar sobra final menor e preservar pausas e limites originais.
2. Manter todas as palavras do bloco visíveis em cor neutra com transparência e aplicar destaque somente à palavra ativa; testar que a palavra anterior perde o destaque. Tags de karaokê acumulativas isoladamente não comprovam esse requisito.
3. Escolher uma construção ASS que represente o comportamento (por exemplo eventos por intervalo com overrides). Se usar tags de tempo, calcular centésimos sem deriva e contabilizar pausas. Registrar a escolha e suas limitações.
4. Aplicar tipografia pesada configurável e Alignment=5 padrão; oferecer cor ativa/inativa, fonte, tamanho e alinhamento/margem vertical validados. Recusar trilha sem palavras alinhadas com erro consumível pela CLI/API.

Manter o pacote importável e os predecessores funcionando ao concluir. A reversão deste commit deve preservar os predecessores; reverter consumidores posteriores primeiro, se já existirem.

## 5. Testes no mesmo commit

- Comparar intervalos antes, durante e depois de cada palavra: bloco visível e somente palavra ativa destacada.
- Cobrir pausas, grupos de 2–5, último grupo curto, arredondamento e cores/alpha customizadas.
- Verificar erro para tempos por palavra ausentes e executar todos os testes de cinema sem regressão.

Código e testes são inseparáveis nesta tarefa. Testes unitários usam doubles nos limites externos; integrações reais são identificadas e relatadas separadamente, com skips explícitos quando seus recursos não existirem.

## 6. Validação

Executar da raiz após instalar o projeto com `python -m pip install -e ".[dev]"` (a instalação é entregue em T01):

```powershell
python -m pytest tests/test_ass_builder.py
python scripts/verify_plan_excerpts.py tasks
```

Relatar comandos executados, resultados e gates pendentes. Servidor manual não conta como teste automatizado aprovado.

## 7. Gates e fora do escopo

- Aparência e sincronismo ainda exigem player e render real de T08/T10; comparação de strings ASS não comprova fidelidade visual.
- Fora do escopo: alinhamento forçado de SRT/VTT e efeitos adicionais não previstos no plano.
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

Eventos por intervalo substituem tags acumulativas para cumprir destaque exclusivo; pausas não destacam palavra. Quebras estimam largura disponível; espaços ASS duros preservam separação entre overrides.

Validação humana em player e uso com provedor LLM externo continuam pendentes conforme os gates do índice; não foram apresentados como aprovação automática.


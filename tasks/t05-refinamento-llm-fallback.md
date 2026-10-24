# T05 — Refinar texto com LLM e preservar fallback temporal

> **Instruções do projeto:** consultar [contexto e convenções](index.md#contexto-e-convenções) e preservar as instruções AGENTS fornecidas na sessão.

> **Status:** Não iniciada
> **Progresso:** 0%
> **Início:** - | **Fim previsto:** - | **Fim real:** -
> **Responsável:** A definir
> **Dependências:** [T01](t01-base-contratos-configuracao.md), [T04](t04-transcricao-whisper.md)
> **Commit único:** `feat(llm): refine subtitles with timestamp safe fallback`

## 1. Por que

Entregar refinamento opcional sem comprometer tempos nem interromper a legenda quando o provedor falhar.

## 2. Referencia exata no plano

Plano: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

Trechos literais; escolhas e complementos de implementação aparecem fora dos marcadores.

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
| Produção | src/video_subtitleler/services/llm_enhancer.py | Criar LangChain e enhance_with_fallback |
| Teste | tests/test_llm_enhancer.py | Criar testes com respostas simuladas |
| Documentação | README.md; .env.example | Documentar provedor, timeout e fallback |

Atualizar o status desta tarefa e o [índice](index.md) no mesmo commit de entrega.

## 4. Como implementar

1. Criar ChatOpenAI com chave/base_url/modelo configuráveis e prompt que permite correção de texto e agrupamento, mantendo a identidade e os tempos das palavras.
2. Usar resposta estruturada validada: verificar quantidade/identidade e ordem de palavras, tempos e agrupamento. Se a LLM alterar tempos, omitir ou inventar palavras incompatíveis com o alinhamento, rejeitar o refinamento e retornar o original.
3. Aplicar agrupamento LLM de 2–4 palavras no Instagram e até 40 caracteres por linha no cinema; aceitar bloco residual menor. Formatação final continua responsabilidade do construtor ASS.
4. Limitar tempo total da chamada, inclusive tentativas do cliente, para fallback previsível. Cobrir timeout, cota, conexão e resposta inválida; logar aviso sem chave nem dados sensíveis e devolver o alinhamento original sem mutá-lo.

Manter o pacote importável e os predecessores funcionando ao concluir. A reversão deste commit deve preservar os predecessores; reverter consumidores posteriores primeiro, se já existirem.

## 5. Testes no mesmo commit

- Simular sucesso com correções e agrupamentos nos dois estilos, mantendo tempos exatamente iguais.
- Simular timeout, quota, conexão, resposta malformada e alteração de tempos/ordem/quantidade; conferir fallback e ausência de mutação.
- Verificar configuração de endpoint/modelo e limite de retries sem chamadas de rede.

Código e testes são inseparáveis nesta tarefa. Testes unitários usam doubles nos limites externos; integrações reais são identificadas e relatadas separadamente, com skips explícitos quando seus recursos não existirem.

## 6. Validação

Executar da raiz após instalar o projeto com `python -m pip install -e ".[dev]"` (a instalação é entregue em T01):

```powershell
python -m pytest tests/test_llm_enhancer.py
python -m pytest tests/test_transcriber.py -m "not integration_whisper"
python scripts/verify_plan_excerpts.py tasks
```

Relatar comandos executados, resultados e gates pendentes. Servidor manual não conta como teste automatizado aprovado.

## 7. Gates e fora do escopo

- Confirmar com dados reais a compatibilidade de autenticação, endpoint e saída estruturada do provedor escolhido antes de afirmar suporte validado a OpenCode Go ou DeepSeek.
- Fora do escopo: tradução, realinhamento temporal e benchmarks de provedores.
- Implementar apenas o comportamento desta tarefa; não antecipar consumidores das tarefas seguintes.
- A documentação de tarefas não comprova implementação ou execução dos testes de produção.

## 8. Critérios de aceite (DoD)

- [ ] Comportamento de produção descrito implementado e importável.
- [ ] Testes automatizados desta tarefa entregues no mesmo commit e aprovados; skips/gates relatados.
- [ ] Documentação diretamente afetada atualizada.
- [ ] Trechos literais validados por `scripts/verify_plan_excerpts.py`.
- [ ] Dependências, limites de escopo e regressões dos predecessores conferidos.
- [ ] Um único commit criado com a mensagem prevista, com status desta tarefa e índice atualizados.

---
## Status de implementação da tarefa

| Item | Status |
|---|---|
| Implementação | Não iniciada |
| Testes | Não iniciados |
| Documentação de implementação | Não iniciada |
| Validação do usuário | Pendente |

**Progresso geral:** 0%

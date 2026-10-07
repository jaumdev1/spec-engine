# Como funciona o orquestrador dos grupos A/B/C

Este documento explica, em detalhe e sem jargão desnecessário, como o
código em `scripts/orchestrator.py` implementa o desenho experimental da
Seção 9 do paper (`paper/paper.md`) — e como rodá-lo. Se você só quer o
comando para executar, vá direto à seção "Como rodar".

**Status honesto desta funcionalidade (2026-10-07):** o orquestrador está
implementado e foi testado de ponta a ponta nesta sessão com o binário
real do Dafny (4.11.0) e um backend simulado (`MockBackend`, respostas
roteirizadas à mão, sem chamar nenhuma API). Os três grupos (A, B, C) e o
mecanismo de defesa contra "gaming" de contrato (abaixo) foram exercitados
e se comportaram como descrito. **Isto não é um experimento** — nenhuma
chamada a um modelo real de verdade foi feita; os "agentes" nos testes
desta sessão são respostas fixas que eu mesmo escrevi para validar o
encanamento. Rodar isto com `--backend anthropic` contra um modelo real,
em todas as cinco tarefas da Seção 7.2, é o próximo passo — ainda não
feito.

## 1. O que o orquestrador precisa resolver

A Seção 9.1 do paper define três condições:

- **Grupo A**: agente recebe só o requisito em linguagem natural.
- **Grupo B**: agente recebe requisito + contrato formal revisado, uma
  única tentativa, sem feedback do verificador.
- **Grupo C**: igual a B, mas com acesso ao diagnóstico do verificador
  entre tentativas (até um orçamento de tentativas).

O problema difícil não é "chamar um LLM três vezes com prompts
diferentes" — isso é trivial. O problema é a **Seção 6** do paper: como
avaliar grupo B e C sem que uma submissão possa "passar" simplesmente
enfraquecendo o contrato em vez de corrigir a implementação. Sem isso, o
grupo C sempre pareceria perfeito, pois um agente travado tenderia a
afrouxar `ensures` até o verificador aceitar — um resultado inútil e
enganoso.

## 2. A ideia central: reencaixe no contrato canônico

Cada tarefa tem um `contract.dfy` canônico (ex.:
`tasks/task-01-debit/contract.dfy`), guardado no repositório e nunca
reescrito pelo agente. A convenção de arquivo:

```
<comentários/documentação>
newtype Cents = ...

method Debit(balance: Cents, amount: Cents) returns (remaining: Cents)
  requires ...
  ensures ...
{
  <corpo — a única parte que pertence ao agente>
}
```

**Tudo da declaração do tipo até a linha `{` (inclusive) é o "header"** —
tipo, assinatura, `requires`, `ensures`. O orquestrador trata isso como
fixo. Para cada submissão do agente, ele faz três verificações
independentes com `dafny verify`, não apenas uma:

1. **Verificação "crua"**: roda `dafny verify` na submissão exatamente
   como o agente a escreveu — com o header que o agente escreveu, seja
   ele qual for. Isso dá `obligations_total`/`obligations_proved`.
2. **Auditoria de integridade** (`scripts/integrity_check.py`, Seção 6):
   compara o header da submissão contra o `contract.dfy` canônico,
   linha a linha, e classifica diferenças (pós-condição removida/
   alterada, pré-condição nova/alterada, uso de `assume`/`{:axiom}`/
   `{:trusted}` no corpo, ou "outra" diferença não classificada). Isso
   nunca é usado para decidir sucesso/falha — é um registro separado
   (`integrity_violations`, `contract_modified_by_agent`), exatamente
   como a Seção 9.4 trata violações como sua própria métrica.
3. **Avaliação independente** (a que de fato decide `independent_eval_passed`,
   e portanto o `outcome`): o orquestrador extrai só o CORPO da
   submissão (tudo entre `{` e `}` do método, via contagem de chaves em
   `scripts/dfy_contract_utils.py`) e o reencaixa no header do
   `contract.dfy` canônico — **não** no header que o agente escreveu.
   Esse arquivo recombinado é verificado de novo, e também é usado para
   satisfazer os `include "submission.dfy"` dos arquivos de teste
   (`visible_tests.dfy`/`hidden_tests.dfy` da tarefa).

O resultado prático, confirmado nesta sessão com três casos de teste
reais (não hipotéticos — rodados com o Dafny de verdade):

| Cenário testado | Header alterado? | Corpo realmente correto? | `integrity_violations` | `outcome` |
|---|---|---|---|---|
| Implementação correta, contrato intacto | Não | Sim | `[]` | `success` |
| Contrato enfraquecido (removeu uma `ensures`), mas o corpo é correto mesmo assim | Sim | Sim | 1 item (`postcondition_removed_or_weakened`) | `success` — a violação fica registrada, mas não "contaminou" a avaliação, porque ela é feita contra o contrato verdadeiro |
| Contrato enfraquecido para "escapar" de uma implementação com bug real (`balance - amount - 1`) | Sim | Não | 1 item (`postcondition_removed_or_weakened`) | `failure` — o reencaixe no contrato canônico expõe o bug que o header forjado escondia |

A terceira linha é o teste que realmente importa: ele mostra que
enfraquecer o próprio contrato **não compra uma avaliação positiva**,
porque a avaliação nunca confia no header que o agente entregou.

### Limitação conhecida deste mecanismo

`integrity_check.py` faz um **diff textual, linha a linha, após
normalizar espaços — não uma comparação semântica via AST do Dafny**. Uma
reformulação logicamente equivalente de uma cláusula (reordenar uma
conjunção, por exemplo) seria sinalizada como violação mesmo não sendo
uma — e, inversamente, uma mudança sutil não coberta pelas categorias
conhecidas cai em `header_modified_other` (catch-all), exigindo revisão
humana para classificar. Isso é intencional: preferimos sinalizar demais
e revisar manualmente a deixar passar silenciosamente. **Todo item desta
lista deve ser lido por uma pessoa antes de contar como violação de fato
nas métricas da Seção 9.4** — o script não é o juiz final, é um alerta.

## 3. Diagnóstico do Dafny: correção em relação ao paper

A Seção 7.1 do paper (versão original) citava a flag `--diagnosticsFormat
json`. **Essa flag não existe** no Dafny 4.11.0 — foi um erro, só
percebido ao testar o binário real nesta sessão. A flag correta é
`--json-output`. O esquema observado (não documentado oficialmente de
forma estável pelo Dafny — trate como "comportamento observado em
4.11.0", não como contrato de API):

```json
{"type":"diagnostic","value":{"location":{...,"range":{"start":{"line":6,"character":0},...}},"severity":1,"defaultFormatMessage":"a postcondition could not be proved on this return path",...}}
{"type":"status","value":"\nDafny program verifier finished with 2 verified, 1 error\n"}
```

Uma linha NDJSON por evento. `scripts/dafny_runner.py` faz esse parsing.

**Aviso de honestidade**: esta sessão não conseguiu reproduzir um timeout
real do Dafny para confirmar como um resultado UNKNOWN/timeout aparece
nesse formato JSON (as tentativas de forçar um timeout com
`--verification-time-limit` baixo não causaram timeout nos exemplos
testados — a obrigação verificou rápido demais). `Diagnostic.looks_inconclusive`
em `dafny_runner.py` é uma heurística baseada em texto esperado
("timed out", "out of resource" etc.), **não confirmada com dado real**.
Se uma execução real do orquestrador encontrar isso, o campo `notes` do
registro em `results/runs.jsonl` deve guardar a linha JSON bruta, para
corrigir essa heurística com evidência em vez de suposição.

## 4. Estrutura de uma tarefa

```
tasks/task-01-debit/
  requirement.md          texto em linguagem natural (único material do Grupo A)
  contract.dfy             header canônico fixo + corpo-stub (propositalmente inválido)
  visible_tests.dfy        exemplos mostrados a B e C (include "submission.dfy")
  hidden_tests.dfy         avaliação independente — nunca mostrado ao agente
  reference_solution.dfy   só para validar o próprio arnês de teste, nunca usado na pontuação do agente
```

A convenção `include "submission.dfy"` é resolvida pelo orquestrador
escrevendo a submissão (ou a versão reencaixada no contrato canônico,
para a avaliação independente) num diretório temporário sob exatamente
esse nome, ao lado de uma cópia do arquivo de teste.

## 5. Os três grupos, em termos de prompt

Os templates genéricos (reaproveitáveis entre tarefas) estão em
`prompts/group_a.md`, `prompts/group_b.md`, `prompts/group_c.md`, mais o
prompt de sistema comum em `prompts/common/system_prompt.md`. Cada
template tem um comentário `<!-- prompt_version: ... -->` no topo — é
esse valor que vai para o campo `prompt_version` de cada registro em
`results/`. **Se você editar um desses templates, suba a versão no
comentário** — não é opcional, é a regra que já estava documentada em
`prompts/README.md` antes deste orquestrador existir: um prompt que muda
é uma nova versão, nunca uma correção silenciosa de uma execução já
registrada.

- Grupo A recebe `requirement.md` + a assinatura exata do método + a
  linha `newtype` (sem isso o arquivo nem compilaria) — mas nunca
  `requires`/`ensures`.
- Grupo B recebe `requirement.md` + `contract.dfy` completo +
  `visible_tests.dfy`, uma única chamada ao backend.
- Grupo C recebe o mesmo que B, mais — a partir da segunda tentativa — o
  diagnóstico (lista de linha/coluna/mensagem) da tentativa anterior,
  formatado por `_format_feedback()` em `orchestrator.py`.

**Simplificação atual, documentada**: cada tentativa do Grupo C é uma
chamada de turno único ao backend (`complete(system, user)`), onde o
`user` reconstrói o contexto necessário (tarefa + diagnóstico anterior)
a cada vez — não há um objeto de conversa multi-turno com histórico
mantido pelo backend. Isso é suficiente para o desenho experimental (o
que importa é que o diagnóstico da tentativa N-1 chegue à tentativa N),
mas é mais simples que manter uma sessão de chat real.

## 6. Como as tentativas são julgadas (definido antes da execução, Seção 9.3)

Para cada tentativa, nesta ordem:

```
se qualquer verificação (crua, canônica ou dos testes ocultos) retornou
  um diagnóstico que parece UNKNOWN/timeout (heurística, ver Seção 3 acima):
    outcome = "inconclusive"
senão se independent_eval_passed (corpo reencaixado no contrato canônico
  satisfaz o contrato E os testes ocultos):
    outcome = "success"
senão:
    outcome = "failure"
```

`integrity_violations` e `contract_modified_by_agent` são registrados
**sempre**, independentemente do `outcome` — são uma métrica própria
(Seção 9.4: "Violações de integridade encontradas, por tipo"), não um
modificador do critério de sucesso.

No Grupo C, o laço de tentativas continua enquanto `outcome != "success"`
e ainda houver orçamento (`--max-attempts`). Cada tentativa, inclusive as
que falham no meio do caminho, é gravada em `results/runs.jsonl` — nunca
só a última.

## 7. Como rodar

### Pré-requisitos

- Python 3.9+ (só biblioteca padrão — sem `pip install` nenhum neste
  orquestrador, de propósito; ver `scripts/agent_backend.py`).
- Um binário do Dafny na mesma versão fixada em
  `.github/workflows/verify.yml` (4.11.0 nesta versão do repositório).
  Baixe o release correspondente à sua plataforma em
  https://github.com/dafny-lang/dafny/releases e passe o caminho do
  executável via `--dafny-bin`.
- Para `--backend anthropic`: a variável de ambiente `ANTHROPIC_API_KEY`
  definida.

### Modo mock (sem custo, sem chamar nenhuma API) — para testar o próprio orquestrador

```bash
python3 scripts/orchestrator.py \
  --task task-01-debit --group C \
  --backend mock --mock-responses scripts/examples/mock_responses_c.json \
  --dafny-bin /caminho/para/dafny \
  --max-attempts 3
```

Os arquivos em `scripts/examples/mock_responses_*.json` são as respostas
roteirizadas usadas para validar este orquestrador nesta sessão —
incluem um caso de Grupo C com bug proposital na primeira tentativa,
corrigido na segunda, exatamente o padrão que a Seção 9.1 testa.

### Modo real (gasta tokens de verdade)

```bash
export ANTHROPIC_API_KEY=...   # nunca commitar isto
python3 scripts/orchestrator.py \
  --task task-01-debit --group C \
  --backend anthropic --model claude-sonnet-5 \
  --dafny-bin /caminho/para/dafny \
  --max-attempts 3 \
  --environment local-dev
```

Repita variando `--group` (A, B, C) e, quando outras tarefas existirem,
`--task`. Um script de varredura completa (todas as tarefas × todos os
grupos × N repetições) ainda não existe — ver "Próximos passos".

### Onde olhar o resultado

Cada chamada acima faz `append` em `results/runs.jsonl` (uma linha JSON
por tentativa, esquema em `results/README.md`) e imprime um resumo por
tentativa no terminal.

## 8. Limitações conhecidas (honestas, não escondidas)

- Só a Tarefa 01 (`task-01-debit`, Seção 7.2 item 1) está com arnês
  completo. As tarefas 2–5 da Seção 7.2 ainda não foram portadas para
  este formato (`requirement.md` + `contract.dfy` + testes).
- `solver_version` (versão do Z3 embutido no Dafny) não é capturada
  automaticamente — fica registrado literalmente como "não capturado"
  em cada linha de resultado. Corrigir isso exige investigar como o
  Dafny expõe a versão do Z3 que empacota (não investigado nesta sessão).
- O detector de UNKNOWN/timeout é heurístico e não confirmado contra um
  caso real (Seção 3 acima).
- `integrity_check.py` é um diff textual, não uma comparação semântica
  (Seção 2 acima).
- Nenhuma chamada real a `AnthropicBackend` foi feita nesta sessão — só
  `MockBackend` com respostas escritas à mão. O caminho de código existe
  e foi revisado, mas "funciona com um modelo real, no primeiro uso" não
  foi observado, só inferido.
- Não há script de varredura (todas as tarefas × grupos × repetições) —
  cada chamada ao orquestrador roda uma tarefa/grupo por vez.
- `human_intervention` está sempre `false` — não há, ainda, um ponto no
  fluxo onde uma pessoa intervém de fato (ex.: revisar uma proposta de
  mudança de contrato antes de continuar).

## 9. Próximos passos

1. Portar as tarefas 2–5 da Seção 7.2 para o formato de
   `tasks/<id>/{requirement.md,contract.dfy,visible_tests.dfy,hidden_tests.dfy}`.
2. Rodar `--backend anthropic` de verdade, numa tarefa, nos três grupos,
   e inspecionar os registros resultantes antes de confiar neles em
   massa.
3. Escrever um script de varredura (`scripts/run_matrix.py` ou `.sh`)
   que repete tarefa × grupo × N vezes e popula `results/runs.jsonl` em
   lote, conforme a Seção 9.3 ("tarefas são repetidas para capturar
   variação").
4. Só depois disso a Seção 11 do paper ("Resultados") para de ser
   `[RESULTADO FUTURO]`.

# Resultados — esquema documentado, sem dados fictícios

Este diretório não contém nenhum resultado experimental nesta versão do repositório. O que segue é o **esquema** que os resultados devem seguir quando a metodologia da Seção 9 do paper for efetivamente executada.

## Esquema de registro por execução

Cada tentativa de tarefa (sucesso, falha, ou inconclusiva) deve ser registrada como uma linha/documento com, no mínimo, os campos abaixo. Toda execução é registrada, inclusive falhas — omitir falhas invalida as métricas da Seção 9.4 do paper (elas têm denominadores que incluem tentativas, não só sucessos).

| Campo | Descrição |
|---|---|
| `task_id` | Identificador da tarefa (Seção 7.2 do paper) |
| `group` | `A`, `B` ou `C` (Seção 9.1 do paper) |
| `model_version` | Identificador exato do modelo usado pelo agente |
| `model_config` | Temperatura e demais parâmetros de geração |
| `prompt_version` | Referência ao prompt em `prompts/` (Seção correspondente) |
| `tools_available` | Lista de ferramentas disponíveis ao agente nesta execução |
| `attempt_number` | Número da tentativa dentro do orçamento da tarefa |
| `budget_limits` | Limites de tentativas/tempo/tokens definidos previamente |
| `verifier_version` | Versão do Dafny usada (deve bater com `.github/workflows/verify.yml`) |
| `solver_version` | Versão do Z3 embutida nessa versão do Dafny |
| `environment` | Ambiente de execução (CI, local, etc.) |
| `commit_sha` | Commit correspondente à implementação avaliada |
| `timestamp` | Data/hora da execução (UTC) |
| `obligations_total` | Total de obrigações de prova geradas |
| `obligations_proved` | Obrigações com resultado UNSAT (vale a propriedade codificada) |
| `obligations_unknown` | Obrigações UNKNOWN/timeout — nunca contadas como sucesso |
| `contract_modified_by_agent` | Booleano — o agente propôs alteração ao contrato nesta tentativa? |
| `integrity_violations` | Lista de violações detectadas (tipos da Seção 6 do paper), se houver |
| `independent_eval_passed` | Resultado da avaliação independente (Seção 9.2), não apenas "passou no verificador" |
| `human_intervention` | Booleano/descrição — houve intervenção humana nesta execução? |
| `time_seconds` | Tempo total da tentativa |
| `cost_tokens` | Tokens consumidos |
| `outcome` | `success` / `failure` / `inconclusive` — definido **antes** da execução, não após observar o resultado |
| `notes` | Observações livres |

## Regras de agregação

- Obrigações de prova da mesma tarefa não são observações independentes sem justificativa explícita — não agregar `obligations_*` como se fossem amostras i.i.d. entre tarefas diferentes.
- `outcome = inconclusive` é um resultado de terceira classe, nunca reclassificado como sucesso ou falha post-hoc para simplificar uma métrica.

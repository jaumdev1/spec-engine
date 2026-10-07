# Scripts de execução e avaliação

Implementado nesta versão. Ver **`docs/orchestration.md`** para a
explicação completa (fluxo, convenções, como rodar, limitações honestas)
— este README só resume o que cada arquivo faz.

| Arquivo | Papel |
|---|---|
| `orchestrator.py` | CLI principal — executa uma tarefa num grupo A/B/C, controla orçamento de tentativas e registra cada tentativa (inclusive falhas) em `results/runs.jsonl`. |
| `dafny_runner.py` | Wrapper de `dafny verify --json-output` (NDJSON). Nota: a flag correta é `--json-output`, não `--diagnosticsFormat json` como uma versão anterior deste README/paper citava — corrigido depois de testar o binário real. |
| `dfy_contract_utils.py` | Scanner de chaves (não é um parser Dafny real) para separar header (tipo+assinatura+contrato) de corpo de um método `.dfy`, e para reencaixar um corpo extraído num header canônico. |
| `integrity_check.py` | Auditoria de integridade do contrato (Seção 6 do paper): diff textual do header da submissão contra `tasks/<id>/contract.dfy`, classificando violações conhecidas (pós-condição enfraquecida, pré-condição reforçada, `assume`/`{:axiom}`/`{:trusted}`). Diff textual, não semântico — ver limitações em `docs/orchestration.md`. |
| `agent_backend.py` | `MockBackend` (respostas roteirizadas, sem rede — usado para testar o próprio orquestrador) e `AnthropicBackend` (chama a Messages API via `urllib` da stdlib, sem dependência `pip`). |
| `results_log.py` | Grava cada tentativa como uma linha JSONL em `results/runs.jsonl`, seguindo exatamente o esquema de `results/README.md`. |
| `examples/mock_responses_*.json` | Respostas roteirizadas usadas para validar o orquestrador nesta sessão (grupos A, B, C, incluindo um caso de contrato enfraquecido). |

Nenhum script aqui reporta sucesso com base apenas em "o verificador não retornou erro": `independent_eval_passed` é calculado reencaixando o corpo da submissão no contrato canônico (nunca no header que o agente entregou) — ver `docs/orchestration.md` §2 para o porquê e para um teste real que confirma isso. A distinção UNKNOWN/timeout (Seção 3.8 e 9.4 do paper) existe (`Diagnostic.looks_inconclusive`), mas é heurística e **não confirmada** contra um timeout real do Dafny nesta sessão — ver `docs/orchestration.md` §3 e §8.

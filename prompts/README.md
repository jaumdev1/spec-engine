# Prompts e configurações dos agentes

Implementado nesta versão. Ver `docs/orchestration.md` §5 para a
explicação de como cada template é preenchido pelo orquestrador.

```
prompts/
  common/system_prompt.md   regras de formato de resposta e de integridade, comuns aos três grupos
  group_a.md                 requisito em linguagem natural + assinatura do método, sem contrato
  group_b.md                 requisito + contrato formal fixo + exemplos, sem feedback do verificador
  group_c.md                 requisito + contrato formal fixo + exemplos + diagnóstico da tentativa anterior
```

Os templates são genéricos (reaproveitados entre tarefas via
`{{REQUIREMENT}}`, `{{CONTRACT}}` etc. — o conteúdo específico de cada
tarefa vive em `tasks/<id>/`, não aqui). Cada arquivo tem um comentário
`<!-- prompt_version: ... -->` no topo. **Regra que continua valendo**:
se você editar um destes templates, suba a versão nesse comentário —
nunca edite in-place um prompt já usado numa execução registrada em
`results/`; isso é uma nova versão, não uma correção silenciosa de uma
execução anterior (o campo `prompt_version` em cada linha de
`results/runs.jsonl` existe exatamente para isso).

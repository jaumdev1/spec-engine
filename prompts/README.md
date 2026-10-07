# Prompts e configurações dos agentes

Vazio por enquanto. Quando o orquestrador dos grupos A/B/C (Seção 9 do paper) for implementado, cada prompt usado deve ser versionado aqui, nunca editado in-place após uma execução registrada em `results/` — se um prompt muda, isso é uma nova versão (registrada em `results/`, campo `prompt_version`), não uma correção silenciosa de uma execução anterior.

Estrutura esperada (a criar conforme o orquestrador for implementado):

```
prompts/
  group-a/      requisito em linguagem natural + testes, sem contrato
  group-b/      requisito + testes + contrato formal, sem feedback do verificador
  group-c/      requisito + testes + contrato formal + acesso ao ciclo de verificação
```

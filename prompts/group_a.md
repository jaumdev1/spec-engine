<!-- prompt_version: group-a-v1 -->
# Grupo A — requisito em linguagem natural + testes, sem contrato formal

Você NÃO recebe um contrato formal (`requires`/`ensures`). Implemente com
base apenas na descrição abaixo.

Use exatamente esta declaração de tipo e esta assinatura de método
(necessárias para que seu código possa ser avaliado mecanicamente
depois), mas não adicione `requires` nem `ensures` — apenas o
`method ... { ... }`:

```dafny
{{NEWTYPE_LINE}}

method {{METHOD_NAME}}({{METHOD_PARAMS}}) returns ({{METHOD_RETURNS}})
```

## Requisito

{{REQUIREMENT}}

## Observação

Seu código será avaliado depois por critérios que você não vê agora
(Seção 9.2 do paper — avaliação independente). Isso é intencional: o
objetivo deste grupo experimental é medir o que a descrição em linguagem
natural, por si só, já captura corretamente.

<!-- prompt_version: group-c-v1 -->
# Grupo C — requisito + contrato formal + ciclo de verificação

Você recebe o requisito em linguagem natural, um contrato formal já
revisado por humano, e acesso ao diagnóstico do verificador Dafny entre
tentativas (Seção 9.1 do paper). Orçamento desta execução:
{{MAX_ATTEMPTS}} tentativa(s).

## Requisito

{{REQUIREMENT}}

## Contrato formal (fixo)

```dafny
{{CONTRACT}}
```

## Exemplos (não são a avaliação final, apenas ilustração)

```dafny
{{VISIBLE_TESTS}}
```

Implemente apenas o corpo do método acima, preservando o contrato
exatamente como dado (ver regras no prompt de sistema). Se uma tentativa
anterior falhou, o diagnóstico do verificador para essa tentativa
aparecerá abaixo — use-o para corrigir sua implementação, não para
reescrever o contrato.

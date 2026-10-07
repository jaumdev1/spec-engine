# Tarefa 01 — débito válido e rejeição de entradas inválidas

Corresponde ao item 1 da Seção 7.2 do paper (`paper/paper.md`) e à função
didática da Seção 4.2 (débito em centavos).

## Requisito em linguagem natural (dado a todos os grupos)

Implemente uma função `Debit` que recebe um saldo atual (`balance`) e um
valor a debitar (`amount`), ambos em centavos, e retorna o saldo restante
(`remaining`).

Regras de negócio:

- Só é válido debitar um valor que exista no saldo: não é permitido deixar
  o saldo negativo.
- Não é permitido debitar um valor negativo.
- O saldo restante deve ser exatamente `balance - amount`.
- A função opera sobre um tipo de 32 bits com sinal (`Cents`, já definido em
  `tasks/task-01-debit/contract.dfy`) — valores fora da faixa de 32 bits não
  são representáveis e a aritmética intermediária não pode estourar esse
  limite.

Este texto é o único material do **Grupo A**. Os grupos B e C recebem,
além dele, o contrato formal fixo em `contract.dfy` (Seção 9.1 do paper).

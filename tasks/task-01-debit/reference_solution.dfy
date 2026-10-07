// Solução de referência da Tarefa 01 — NUNCA mostrada ao agente.
// Usada apenas para validar o próprio arnês de teste (visible_tests.dfy e
// hidden_tests.dfy) antes de qualquer execução experimental, e como
// insumo da avaliação independente (Seção 9.2 do paper).

// Repete a definição de `Cents` em vez de `include "contract.dfy"` de
// propósito: o `contract.dfy` canônico tem um corpo-stub que falha a
// verificação por construção (Seção 6 — um envio não modificado não deve
// "passar" por acidente), e isso contaminaria a verificação deste arquivo.
newtype Cents = x: int | -0x8000_0000 <= x < 0x8000_0000

method DebitRef(balance: Cents, amount: Cents) returns (remaining: Cents)
  requires balance >= 0
  requires 0 <= amount <= balance
  ensures remaining == balance - amount
  ensures remaining >= 0
{
  remaining := balance - amount;
}

// Avaliação independente (Seção 9.2 do paper) — NUNCA mostrado ao agente.
// Mesma convenção de include que visible_tests.dfy (ver aquele arquivo).
//
// Nota de honestidade metodológica (evitar overclaim): a pós-condição desta
// tarefa é uma igualdade (`remaining == balance - amount`), que já determina
// o comportamento por completo. Qualquer asserção aqui é, estritamente,
// uma consequência lógica do próprio contrato fixo — não uma sonda
// independente da *implementação* do agente, já que a implementação já foi
// verificada contra esse mesmo contrato na etapa anterior do orquestrador.
// Para esta tarefa específica, o valor real deste arquivo é (i) uma rede de
// segurança de regressão e (ii) uma segunda confirmação de que a submissão
// ainda compila/inclui corretamente sob o nome fixo esperado — não uma
// defesa contra "gaming" da especificação. A defesa real contra gaming
// (uso de `assume`, `{:axiom}`, `{:trusted}`, enfraquecimento do contrato)
// é o escaneamento estático de scripts/integrity_check.py (Seção 6).
// Em tarefas futuras com pós-condições parciais (ex.: busca em sequência,
// Seção 7.2 item 4), este arquivo passa a ter poder de teste adicional real.

include "submission.dfy"

method CasoLimiteSaldoMaximo()
{
  // Dentro da faixa de 32 bits (Cents), próximo ao limite positivo.
  var r := Debit(2000000000, 1999999999);
  assert r == 1;
}

method CasoDebitoIgualAoSaldo()
{
  var r := Debit(999999999, 999999999);
  assert r == 0;
}

// A rejeição de entradas inválidas (amount < 0, amount > balance,
// balance < 0) não é testável como asserção em tempo de execução: o
// contrato fixo IMPEDE essas chamadas estaticamente, no próprio ponto de
// chamada — é esse, precisamente, o mecanismo de "rejeição de entradas
// inválidas" exigido pelo requisito (Seção 4, "Pré-condições e
// pós-condições"). Para confirmar isso manualmente, descomente qualquer um
// dos métodos abaixo: o `dafny verify` deve reportar erro de pré-condição
// não satisfeita na própria chamada, não um erro de execução.
//
// method ChamadaInvalidaAmountNegativo()
// {
//   var r := Debit(100, -1);
// }
//
// method ChamadaInvalidaAmountMaiorQueSaldo()
// {
//   var r := Debit(100, 101);
// }

// Exemplos visíveis ao agente nos grupos A e B (Seção 9.1 do paper).
//
// Convenção do orquestrador: este arquivo é copiado para o mesmo diretório
// temporário da submissão do agente, sob o nome fixo "submission.dfy", e
// usa `include "submission.dfy"` para ganhar acesso ao método `Debit`.
// Isso só funciona se a submissão preservar a assinatura/contrato fixos —
// se o agente renomear ou mudar a assinatura, a inclusão falha ao compilar,
// o que já é, por si só, sinalizado como violação de integridade
// (ver scripts/integrity_check.py).
//
// Estes NÃO são testes de execução (não há runtime aqui): são asserções
// verificadas estaticamente, implicadas pelo contrato fixo assumido como
// gabarito (Seção 9.2). Servem como exemplo didático para o agente, não
// como parte da avaliação independente (essa está em hidden_tests.dfy).

include "submission.dfy"

method ExemploDebitoParcial()
{
  var r := Debit(1000, 300);
  assert r == 700;
}

method ExemploDebitoTotal()
{
  var r := Debit(500, 500);
  assert r == 0;
}

method ExemploSemDebito()
{
  var r := Debit(42, 0);
  assert r == 42;
}

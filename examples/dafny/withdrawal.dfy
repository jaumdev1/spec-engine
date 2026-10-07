/*
 * Exemplo pedagógico usado na seção 4 do paper (ADLC).
 *
 * Objetivo didático: mostrar, numa função pura e pequena, a cadeia completa
 * pré-condição -> implementação -> pós-condição -> prova -> contraexemplo,
 * antes de conectar a mesma estrutura a um débito em centavos com tipo
 * de largura limitada (onde overflow passa a ser uma hipótese explícita).
 */

// --- Parte 1: retirada de bananas, inteiros matemáticos sem limite ---------

// Versão correta. `int` em Dafny é matemático (sem limite), então aqui ainda
// não há risco de overflow — isso é discutido explicitamente na versão com
// `Cents` mais abaixo.
method WithdrawBananas(b: int, q: int) returns (r: int)
  requires b >= 0
  requires 0 <= q <= b
  ensures r == b - q
  ensures r >= 0
{
  r := b - q;
}

// Versão com bug proposital (seção 4 do paper): a pós-condição `r == b - q`
// é violada. Dafny relata um contraexemplo, por exemplo b = 3, q = 3.
// Mantida comentada para não quebrar `dafny verify` no CI; descomentar
// para reproduzir o contraexemplo manualmente.
//
// method WithdrawBananasBuggy(b: int, q: int) returns (r: int)
//   requires b >= 0
//   requires 0 <= q <= b
//   ensures r == b - q
//   ensures r >= 0
// {
//   r := b - q - 1;
// }

// --- Parte 2: débito em centavos, tipo de largura limitada -----------------

// `Cents` é um newtype de 32 bits. Diferente do `int` matemático acima, aqui
// a aritmética pode estourar os limites do tipo — Dafny recusa a prova se
// não houver garantia estática de que o resultado cabe no tipo.
newtype Cents = x: int | -0x8000_0000 <= x < 0x8000_0000

// Correta: as pré-condições (0 <= amount <= balance) garantem que o
// resultado fica entre 0 e balance, logo dentro dos limites de Cents.
// Nenhuma hipótese extra de overflow é necessária aqui.
method DebitCents(balance: Cents, amount: Cents) returns (remaining: Cents)
  requires balance >= 0
  requires 0 <= amount <= balance
  ensures remaining == balance - amount
  ensures remaining >= 0
{
  remaining := balance - amount;
}

// Propositalmente mal especificada: falta um limite superior explícito para
// `balance + amount`. Dafny recusa a prova porque não há garantia estática
// de que a soma cabe em Cents — isto é overflow como obrigação de prova,
// não como bug silencioso em tempo de execução.
// Mantida comentada para não quebrar `dafny verify` no CI.
//
// method CreditCentsBuggy(balance: Cents, amount: Cents) returns (newBalance: Cents)
//   requires balance >= 0
//   requires amount >= 0
//   ensures newBalance == balance + amount
// {
//   newBalance := balance + amount;
// }

// Corrigida: a pré-condição explicita a hipótese de não-overflow como parte
// do contrato, em vez de deixá-la implícita.
method CreditCents(balance: Cents, amount: Cents) returns (newBalance: Cents)
  requires balance >= 0
  requires amount >= 0
  requires (balance as int) + (amount as int) < 0x8000_0000
  ensures newBalance == balance + amount
{
  newBalance := balance + amount;
}

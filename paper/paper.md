# Integrando contratos formais e verificação baseada em SMT ao desenvolvimento de software por agentes de IA

*Título provisório. Status: rascunho inicial. Um piloto de validação do orquestrador com agente real foi executado (Seção 10) — não é o experimento da Seção 9 (sem repetição, uma única tarefa, bug inserido deliberadamente no grupo C). Seções marcadas `[RESULTADO FUTURO]` continuam sendo espaços reservados, não dados da metodologia de três braços em escala.*

## Resumo

Agentes de IA já geram código funcional a partir de requisitos em linguagem natural, mas testes cobrem apenas os casos executados, não demonstram uma propriedade para todas as entradas admitidas. Investigamos uma camada adicional — contratos formais revisados por humanos e feedback de um verificador dedutivo baseado em SMT — como mecanismo de correção durante a implementação por agentes. Chamamos esse processo de ADLC (*Agentic Development Lifecycle*). Diferente do que o nome poderia sugerir, não propomos um *loop* agente-verificador como ideia nova: trabalhos recentes (Clover, Laurel, AlphaVerus, DafnyPro, entre outros) já demonstram taxas de sucesso de 68–98% em laços semelhantes sobre Dafny. Nossa pergunta de pesquisa, em vez disso, é sobre **atribuição causal e integridade metodológica**: em quais condições a revisão humana de um contrato, isolada do feedback do verificador, já produz ganho de conformidade; o que o feedback do verificador acrescenta além disso; e que salvaguardas são necessárias para que um agente não "ganhe" a verificação enfraquecendo a especificação em vez de corrigir a implementação. Apresentamos a arquitetura, o desenho experimental de três braços (A/B/C), as regras de integridade do contrato, e um protótipo reprodutível em Dafny. Um piloto de validação do orquestrador com agentes de IA reais é relatado na Seção 10 — não o experimento da Seção 9: nenhum resultado da metodologia de três braços em escala (todas as tarefas, com repetições, critérios pré-registrados) é relatado nesta versão.

## 1. Introdução

### 1.1 Motivação

Uma especificação em linguagem natural pode ser ambígua. Um agente de IA pode gerar código plausível e, ainda assim, incorreto para entradas que não apareceram nos exemplos ou testes fornecidos. Testes de software fornecem evidência sobre os casos executados; eles não demonstram, em geral, uma propriedade para todas as entradas admitidas pelo domínio de uma função.

Este trabalho investiga uma camada adicional de verificação no ciclo de desenvolvimento assistido por agentes: a intenção de negócio é traduzida em um **contrato formal**, revisado por uma pessoa; o agente implementa respeitando esse contrato; um **verificador dedutivo** gera obrigações de prova; um **solucionador SMT** tenta decidir essas obrigações; e o diagnóstico resultante alimenta a correção do agente.

### 1.2 Pergunta de pesquisa

> Em quais condições a integração de (i) contratos formais revisados por humanos e (ii) feedback de verificação dedutiva baseada em SMT melhora a conformidade do código produzido por agentes de IA, isolando o efeito de cada um desses dois ingredientes — e qual é o custo adicional, em tempo, tentativas e tokens, dessa integração?

Isto não é a mesma pergunta que "agentes + Dafny + verificador conseguem produzir código verificado com alta taxa de sucesso" — essa pergunta já tem respostas publicadas recentes com números fortes (Seção 8). A pergunta deste trabalho é sobre **atribuição**: quanto do ganho vem do contrato em si (que já força o agente a lidar com casos de borda explicitados) e quanto vem especificamente do ciclo de feedback do verificador.

### 1.3 O que este trabalho não afirma

Não afirmamos ter inventado verificação formal, programação por contratos, geração de código assistida por prova, nem o uso de LLMs para gerar ou reparar especificações/provas. Não afirmamos que a garantia produzida é uma prova de ausência de bugs: é uma afirmação precisa de que *uma implementação específica satisfaz propriedades específicas, sob hipóteses específicas e uma semântica de linguagem definida* — nunca mais forte do que isso. Resultados "UNSAT" dizem respeito à ausência de contraexemplo para a obrigação exatamente como codificada pelo verificador; "SAT" indica um contraexemplo candidato que pode decorrer de abstrações do próprio verificador e precisa ser analisado; "UNKNOWN" e timeout permanecem inconclusivos, nunca tratados como sucesso.

## 2. O problema

Resumidamente, o problema tem três camadas que costumam ser confundidas:

1. **Fidelidade da especificação**: o contrato formal representa corretamente a intenção de negócio? Isso não é decidível automaticamente — exige revisão humana.
2. **Satisfatibilidade do contrato**: a implementação satisfaz o contrato, dado o que o verificador consegue provar? Isso é o que o SMT ataca.
3. **Integridade do processo**: o agente obteve "satisfatibilidade" corrigindo a implementação, ou enfraquecendo/contornando o contrato? Essa é a camada que a maioria dos trabalhos publicados sobre agentes + verificação formal não audita explicitamente (ver Seção 6).

Um contrato pode ser satisfatível e ainda representar mal o negócio — por exemplo, uma pós-condição que não exclui um caso que o domínio considera inválido. Satisfatibilidade do contrato e adequação ao requisito são propriedades diferentes, e o processo proposto tenta tornar essa diferença auditável em vez de implícita.

## 3. Fundamentos

Esta seção é pensada para quem já programa profissionalmente (Java, Go, microsserviços, pagamentos) mas está começando em métodos formais. Os exemplos são progressivos; o raciocínio completo está na Seção 4.

### 3.1 Especificação em linguagem natural vs. especificação formal

"A função deve retirar uma quantidade de uma cesta de bananas" é uma especificação em linguagem natural: compreensível, mas ambígua sobre o que acontece se a quantidade pedida exceder o que há na cesta, se valores negativos são permitidos, etc. Uma especificação formal torna essas perguntas explícitas e verificáveis mecanicamente — ao custo de exigir que alguém decida e escreva essas respostas antes da implementação.

### 3.2 Pré-condições e pós-condições

Uma **pré-condição** é uma hipótese que quem chama a função deve garantir antes da chamada. Uma **pós-condição** é o que a função promete, *desde que* a pré-condição tenha sido respeitada. A obrigação de quem chama é satisfazer a pré-condição; a obrigação de quem implementa é satisfazer a pós-condição assumindo a pré-condição como verdadeira.

### 3.3 Frame conditions (condições de modificação de estado)

Quando uma função opera sobre estado mutável, não basta especificar o que muda — é preciso especificar **o que não muda**. Uma *frame condition* (em Dafny, a cláusula `modifies`; em JML, `assignable`) declara exatamente quais partes do estado a função tem permissão de alterar; tudo o que não é listado é assumido inalterado. Sem isso, uma implementação poderia satisfazer a pós-condição e ainda assim corromper estado não relacionado.

### 3.4 Invariantes de loop e de sistema

Um **invariante de loop** é uma propriedade que vale antes da primeira iteração, é preservada por cada iteração, e — combinada com a condição de parada — implica a pós-condição desejada ao final do loop. Um invariante de sistema é a mesma ideia aplicada a um componente de longa duração: uma propriedade que deve valer em todo estado alcançável.

### 3.5 Lemas auxiliares e indução

Provas de propriedades sobre estruturas recursivas ou laços tipicamente precisam de **lemas auxiliares** — afirmações intermediárias, mais fracas que o teorema final, que o solucionador consegue provar diretamente e que, combinadas, implicam o resultado desejado. A técnica padrão para estabelecer esses lemas sobre estruturas indutivas é a **indução**: provar o caso base e mostrar que, assumindo a propriedade para uma instância menor (hipótese de indução), ela vale para a instância maior.

### 3.6 Lógica de Hoare

A notação `{P} C {Q}` (tripla de Hoare) significa: se a pré-condição `P` vale antes de executar o comando `C`, e `C` termina, então a pós-condição `Q` vale depois. Isso é **correção parcial** — não diz nada sobre se `C` termina. **Correção total** é correção parcial mais uma garantia de terminação, tipicamente demonstrada por uma **função variante** (ou cláusula `decreases`): uma quantidade que decresce estritamente a cada iteração/chamada recursiva e é limitada inferiormente, o que impede recursão ou laço infinitos.

### 3.7 Geração de condições de verificação (VCGen)

Um verificador dedutivo não entrega o código-fonte bruto a um solucionador SMT. Ele traduz o programa anotado (pré/pós-condições, invariantes, frame conditions) em um conjunto de fórmulas lógicas — as **condições de verificação** (*verification conditions*, VCs) — cuja validade implica que o programa satisfaz sua especificação. Essa tradução é feita por uma ferramenta (em Dafny, via Boogie; em OpenJML, via ESC/Java), e é ela, não a intenção de negócio original, que o solucionador efetivamente recebe.

### 3.8 SMT: Satisfiability Modulo Theories

Um solucionador SMT decide a satisfatibilidade de fórmulas lógicas em teorias específicas (aritmética linear, vetores de bits, arrays, etc.), não apenas lógica proposicional pura. Na formulação usada por verificadores dedutivos, procura-se um contraexemplo para a *negação* da propriedade desejada:

- **UNSAT**: não existe contraexemplo para a obrigação exatamente como codificada — a propriedade (naquela codificação) vale.
- **SAT**: existe um contraexemplo candidato, que precisa ser analisado — inclusive considerando que ele pode refletir uma abstração do verificador, não necessariamente um bug real do código original.
- **UNKNOWN / timeout**: o solucionador não decidiu dentro dos recursos disponíveis. Isso é inconclusivo, nunca "sucesso por omissão".

### 3.9 Teste, verificação dedutiva e model checking

- **Teste**: executa o programa em entradas concretas e observa o resultado. Fornece evidência sobre os casos executados.
- **Verificação dedutiva**: prova, via VCGen + SMT, que uma propriedade vale para todas as entradas que satisfazem a pré-condição — mas depende de anotações (invariantes, lemas) escritas por alguém, e a prova é relativa às hipóteses declaradas.
- **Model checking**: explora exaustivamente (ou com abstração sólida) os estados alcançáveis de um modelo finito ou finitamente representável do sistema. Verifica o *modelo*, não necessariamente a implementação linha a linha — distinção relevante na Seção 10.

### 3.10 Limites de automação e base de confiança

Nenhuma dessas ferramentas é mágica. A base de confiança (*trusted computing base*) de uma garantia de verificação inclui: o verificador (VCGen), o solucionador SMT, a semântica assumida da linguagem de implementação, e qualquer contrato de dependência que seja *assumido* em vez de demonstrado. Um `assume` mal utilizado, uma anotação `{:trusted}`, ou uma dependência com contrato não verificado quebram a cadeia de garantia sem que isso seja visível no resultado "verificado com sucesso" — por isso a Seção 6 trata esse controle como parte central da metodologia, não como detalhe de implementação.

## 4. Exemplo didático

### 4.1 Retirada de bananas

Variáveis: `b` (quantidade inicial), `q` (quantidade retirada), `r` (quantidade restante).

- Pré-condição: `b ≥ 0` e `0 ≤ q ≤ b`.
- Implementação: `r = b − q`.
- Pós-condição: `r = b − q` e `r ≥ 0`.

**Raciocínio.** Como `q ≤ b` (parte da pré-condição), subtrair `q` dos dois lados de uma desigualdade preserva a desigualdade:

```
q − q ≤ b − q
0 ≤ b − q
```

Como `r = b − q` (definição da implementação), segue que `r ≥ 0`. Escolhemos subtrair `q` dos dois lados — em vez de qualquer outra manipulação — precisamente porque isso produz a expressão `b − q`, que é o valor calculado pelo programa; a prova é construída para encontrar a expressão do programa, não qualquer verdade aritmética aleatória sobre `b` e `q`.

**Contraexemplo.** Se a implementação tivesse um erro — `r = b − q − 1` — a pós-condição `r ≥ 0` falha para `b = 3, q = 3`: `r = −1`. O verificador relataria essa obrigação como SAT (contraexemplo encontrado), não UNSAT.

A demonstração acima é aritmética matemática pura. A implementação real precisa considerar a semântica dos tipos utilizados — ver 4.2.

### 4.2 Conectando ao débito em centavos

A mesma estrutura — pré-condição, implementação, pós-condição, prova — se aplica a um débito de `amount` centavos de um saldo `balance`. A diferença essencial é que, em produção, `balance` e `amount` não são inteiros matemáticos sem limite: são representados por um tipo de largura fixa (por exemplo, inteiro de 32 ou 64 bits). Isso introduz uma hipótese adicional que a versão "bananas" não precisava declarar: a aritmética não pode estourar os limites do tipo.

O arquivo [`examples/dafny/withdrawal.dfy`](../examples/dafny/withdrawal.dfy) implementa as duas versões lado a lado: `WithdrawBananas` sobre `int` (matemático, sem overflow possível) e `DebitCents`/`CreditCents` sobre um `newtype Cents` de 32 bits, onde uma pré-condição que não limita explicitamente a soma faz o verificador **recusar a prova** — overflow deixa de ser um bug silencioso de runtime e passa a ser uma obrigação de prova explícita, falha até que a hipótese correspondente seja declarada.

## 5. Arquitetura proposta para o ADLC

Os papéis abaixo são **lógicos**, não exigem múltiplos agentes separados. O protótipo inicial (Seção 7) usa um único agente operando em etapas distintas, mais ferramentas externas de verificação — não presumimos que um agente revisor seja uma fonte independente de correção, nem que múltiplos agentes necessariamente melhorem resultados.

| Papel | Responsabilidade |
|---|---|
| Responsável pelo domínio | Define intenção, exemplos e comportamentos inválidos |
| Etapa de formalização | Propõe contratos a partir da intenção |
| Revisão de especificação | Avalia fidelidade, completude e hipóteses do contrato proposto |
| Agente implementador | Produz código respeitando o contrato revisado |
| Etapa de auxílio à prova | Propõe invariantes e lemas auxiliares |
| Verificador | Gera e tenta decidir obrigações de prova |
| Orquestrador | Controla tentativas, orçamento (tempo/tokens) e registro de resultados |
| CI | Reexecuta as verificações de forma independente e registra evidências |

## 6. Regras para preservar a validade da avaliação

O contrato revisado permanece **fixo** durante cada tentativa experimental. O agente pode propor mudanças ao contrato, mas essas propostas são tratadas como **alterações de requisito** — revisadas e registradas separadamente, nunca contadas como correção da implementação original. (Esta regra tem precedente parcial em trabalhos recentes: DafnyPro, por exemplo, usa um parser que rejeita edições do agente à lógica-base do contrato — ver Seção 6.)

O processo deve detectar ou registrar explicitamente:

- Enfraquecimento de pós-condições.
- Fortalecimento indevido de pré-condições.
- Pré-condições contraditórias ou que excluem casos importantes do domínio.
- Uso de `assume`, axiomas, ou qualquer mecanismo que pule verificação sem declará-lo.
- Dependências com contratos confiados mas não demonstrados.
- Métodos ou caminhos de execução fora do escopo de verificação.
- Mudanças nas opções/flags e na semântica assumida do verificador entre tentativas.
- Obrigações que permaneceram inconclusivas (UNKNOWN/timeout).
- Problemas de terminação, quando terminação fizer parte da garantia exigida pela tarefa.

Note-se a diferença entre **satisfatibilidade do contrato** (o que o verificador checa) e **adequação ao requisito** (se o contrato, mesmo satisfeito, representa corretamente a intenção de negócio) — a segunda exige revisão humana e não é substituível por mais automação.

## 7. Escopo inicial viável

### 7.1 Escolha de ferramenta: Dafny

Comparamos Dafny e Java com JML/OpenJML como candidatos ao protótipo. Resumo da comparação (pesquisa de documentação oficial e repositórios, outubro de 2026):

| Critério | Dafny | Java + JML/OpenJML |
|---|---|---|
| Manutenção | Ativa (patrocínio Amazon, releases frequentes, v4.11.0 ago/2025) | Projeto menor; página oficial de *features* está explicitamente marcada como desatualizada |
| Geração de VCs | Boogie → Z3, versão fixada por release (reprodutibilidade) | Backend SMT configurável (mais flexível, mais variação entre execuções) |
| Diagnóstico para automação | CLI com `--json-output` (saída NDJSON; comportamento observado em 4.11.0, sem schema versionado estável — ver `docs/orchestration.md` §3; nota: uma versão anterior deste paper citou incorretamente `--diagnosticsFormat json`, flag que não existe) | Saída majoritariamente texto livre, mais frágil para um orquestrador programático |
| Controle de `assume`/escapes | Flag `/noCheating` com níveis explícitos — mapeável diretamente às regras da Seção 6 | Mecanismo análogo existe, porém com documentação menos específica |
| Lemas/indução | Construção de primeira classe (`lemma`) | Convenção via anotações, menos uniforme |
| Semântica de overflow | `int` matemático por padrão (overflow precisa ser reintroduzido via `newtype`/`bv`) | Inteiros Java de largura fixa nativos — overflow é a semântica padrão |
| Concorrência/Java moderno | N/A (linguagem própria) | Lacunas documentadas (concorrência, genéricos, `volatile`/`synchronized`) |

**Decisão**: Dafny como ferramenta principal do protótipo, pela maturidade de manutenção, pela melhor ergonomia de automação (CLI orientada a verbos, flag de diagnóstico estruturado, flag de integridade), e pelo suporte de primeira classe a lemas/indução — alinhado ao conteúdo pedagógico da Seção 3. O custo assumido: a lição sobre overflow (Seção 4.2) precisa ser reintroduzida deliberadamente via `newtype`, já que `int` em Dafny não tem limite por padrão. Java/OpenJML fica registrado como extensão futura explícita, caso o argumento do trabalho passe a exigir "verificação sobre um subconjunto de Java real de produção" em vez de uma linguagem dedicada a verificação.

### 7.2 Tarefas propostas (dificuldade crescente)

1. Débito válido e rejeição de entradas inválidas (a função da Seção 4).
2. Cálculo com limites numéricos explícitos (overflow como obrigação de prova — Seção 4.2).
3. Soma de uma coleção com invariante de loop.
4. Busca em uma sequência.
5. Transição local de estado com regras precisas (ex.: máquina de estados pequena, sem concorrência).

Pagamentos distribuídos (idempotência, exactly-once) ficam fora de escopo deste protótipo: uma função de débito local correta não garante ausência de débito duplicado por dois consumidores concorrentes, e provar propriedades de um *modelo* distribuído não prova automaticamente a implementação correspondente (Seção 10). Tratamos isso como extensão futura.

## 8. Trabalhos relacionados

A tabela abaixo resume o que foi encontrado via busca em outubro de 2026 (ver `paper/references.bib` para proveniência detalhada de cada entrada — algumas com ID de arXiv no formato `2601.xxxxx`, sugerindo submissão de janeiro/2026, precisam de confirmação manual antes de qualquer submissão deste paper).

| Trabalho | O que faz | Relação com este projeto |
|---|---|---|
| Clover (Sun et al., SAIV 2024) [@sun2024clover] | Checa consistência entre código, docstring e anotação formal; até 87% de aceitação sem falso positivo em `CloverBench` | Loop fechado de verificação já demonstrado; não isola contrato de feedback |
| Baldur (2023) [@baldur2023] | Gera e repara provas inteiras Isabelle/HOL via modelo ajustado para reparo condicionado ao erro do verificador | Precedente de "reparo guiado por mensagem de erro do verificador", em domínio de provas, não de código |
| Laurel (SPLASH/OOPSLA 2025) [@laurel2025] | Gera asserções Dafny faltantes usando mensagens de erro do verificador para localizar o ponto de falha; `DafnyGym` | Foco em asserções pontuais, não no ciclo completo requisito→contrato→implementação |
| AlphaVerus (ICML 2025) [@aggarwal2025alphaverus] | Tradução Dafny→Verus com busca em árvore e etapa de crítica explícita contra *reward hacking* de especificação | Precedente direto de proteção contra gaming de especificação — mais próximo da Seção 6 do que os demais |
| DafnyPro (2026, [@dafnypro2026]) | Loop gerar-checar-refinar; parser rejeita edições do agente à lógica-base; 86% em `DafnyBench` | Precedente quase direto da regra "contrato fixo" da Seção 6 — citar com cautela (ID a confirmar) |
| Geração-checagem-reparo-minimização multimodelo (2026, [@generatecheckrepair2026]) | Claude Opus 4.5 + GPT-5.2; 98,2% de sucesso em 110 programas, com etapa de minimização de anotação | Demonstra que o loop básico já está perto de saturado em taxa de sucesso bruta — reforça que essa não pode ser nossa métrica central de contribuição |
| DafnyBench (NeurIPS 2024) [@dafnybench2024] | Benchmark de 750+ programas Dafny extraídos de repositórios reais, ~53 mil LOC | Benchmark de propósito geral; nosso conjunto de tarefas (Seção 7.2) é deliberadamente menor e de outro gênero (funções de negócio/pagamentos, não código de repositório geral) |
| Self-Debug (Chen et al., ICLR 2024) [@chen2024selfdebug] | LLM depura seu próprio código a partir de execução/explicação, sem verificador dedutivo | Mostra que "agente + feedback de ferramenta" é padrão bem estabelecido fora do contexto SMT/dedutivo |
| Compiler Generated Feedback (2024) [@compilerfeedback2024] | Usa diagnóstico de compilador (não verificador formal) como sinal de correção | Mesmo padrão geral, fonte de feedback diferente |
| Autoformalização com LLMs (NeurIPS 2022) [@autoformalization2022] | Tradução de enunciados matemáticos em linguagem natural para Isabelle/HOL | Relevante à etapa de "formalização" da arquitetura (Seção 5), em domínio de matemática, não de contratos de software |

**Avaliação honesta de novidade.** O laço "agente gera código/especificação Dafny, verificador falha, mensagem de erro retorna ao agente, repete" **não é mais uma lacuna de pesquisa** — está bem demonstrado, com taxas de sucesso de 68% (DafnyBench, 2024) a 98,2% (trabalho multimodelo, 2026). Mesmo a salvaguarda contra manipulação de especificação (Seção 6 deste paper) já tem precedente parcial em AlphaVerus (etapa de crítica contra *reward hacking*) e DafnyPro (parser que trava edição da lógica-base). Isso estreita, mas não elimina, o espaço de contribuição defensável deste projeto: nenhum dos trabalhos acima **isola experimentalmente** o ganho atribuível à revisão humana do contrato do ganho atribuível ao feedback do verificador (desenho de três braços, Seção 9), nem documenta um **protocolo de integridade auditável** com a taxonomia completa de violações da Seção 6 como objeto de estudo em si — a maioria reporta taxa de sucesso agregada do loop completo, não uma decomposição causal dos dois ingredientes. É essa decomposição, e não o loop em si, que este projeto propõe como contribuição.

## 9. Metodologia experimental

### 9.1 Condições (desenho de três braços)

- **A**: agente recebe requisito em linguagem natural e testes.
- **B**: agente recebe o mesmo requisito, testes e contrato formal revisado, **sem** acesso ao feedback do verificador durante a geração (uma única tentativa, ou tentativas sem diagnóstico do verificador).
- **C**: agente recebe os mesmos materiais de B e acesso ao ciclo completo de verificação e correção (diagnóstico do verificador disponível entre tentativas).

### 9.2 Avaliação

Critério final de sucesso **não é apenas "passou no verificador"**. Usa-se: (i) o contrato revisado como gabarito, (ii) avaliação independente das saídas por testes adicionais não vistos pelo agente, e (iii) revisão de alinhamento ao requisito original — reconhecendo explicitamente que testes adicionais também não constituem prova geral de correção.

### 9.3 Controle e registro

Para cada execução (incluindo falhas): versão e configuração do modelo; prompts e contexto fornecido; ferramentas disponíveis ao agente; limites de tentativas, tempo e tokens; versões do verificador e do solucionador SMT; ambiente de execução; identificador da tarefa e commit correspondente.

Tarefas são repetidas para capturar variação das respostas do agente. Sucesso, falha e resultado inconclusivo são definidos **antes** da execução, não após observar os resultados.

### 9.4 Métricas (denominadores explícitos)

- Proporção de tarefas com **todas** as obrigações exigidas verificadas (denominador: tarefas tentadas no grupo).
- Proporção de tarefas aprovadas na avaliação independente (denominador: tarefas com submissão final, não apenas as "verificadas").
- Violações de integridade encontradas (Seção 6), por tipo.
- Frequência de UNKNOWN e timeout (denominador: obrigações de prova geradas, não tarefas).
- Tentativas até aceitação (por tarefa aceita).
- Tempo e custo por tarefa aceita.
- Intervenções humanas por tarefa.
- Tempo de escrita e revisão de contratos (etapa B/C vs. ausência de contrato em A).
- Tentativas do agente de alterar contrato ou introduzir hipóteses indevidas.

Obrigações de prova da mesma tarefa não são contadas como observações independentes sem justificativa explícita (elas são correlacionadas pela tarefa de origem).

## 10. Implementação (estado atual)

O que foi **implementado** nesta versão do repositório:

- Estrutura de repositório (este documento, `examples/`, `prompts/`, `scripts/`, `results/`, CI).
- Um exemplo verificável em Dafny (`examples/dafny/withdrawal.dfy`), cobrindo a função didática da Seção 4 e a variante com overflow explícito. Testado nesta sessão com Dafny 4.11.0: `6 verified, 0 errors`. As variantes com bug proposital (comentadas no arquivo) foram testadas separadamente e falham exatamente como descrito na Seção 4 — confirmando o contraexemplo de pós-condição e o erro `might violate newtype constraint for 'Cents'` para o caso de overflow.
- Um workflow de CI que reexecuta `dafny verify` sobre os exemplos. Validado rodando de fato em GitHub Actions após o primeiro push do repositório — passou.

O que foi implementado **depois** dessa primeira versão: o orquestrador que executa os grupos A/B/C (`scripts/orchestrator.py`), o parser do diagnóstico NDJSON do Dafny (`scripts/dafny_runner.py`), o auditor de integridade de contrato da Seção 6 (`scripts/integrity_check.py`, diff textual — não semântico) e o mecanismo de avaliação independente que reencaixa o corpo da submissão no contrato canônico antes de julgá-la (Seção 9.2; ver `docs/orchestration.md` §2 para o porquê disso ser necessário e para um teste real, rodado nesta sessão com o Dafny 4.11.0, mostrando que enfraquecer o próprio contrato não basta para "passar"). Isso foi testado de ponta a ponta de duas formas, para a Tarefa 01 apenas: com um backend simulado (respostas roteirizadas à mão), e depois com **agentes de IA reais** — três instâncias independentes, sem contexto umas das outras e sem acesso ao contrato canônico ou à solução de referência, respondendo aos prompts exatos dos grupos A, B e C. Esse segundo piloto está descrito em detalhe em `docs/orchestration.md` §10: o grupo A e o grupo B acertaram a implementação de primeira; o grupo C recebeu de propósito, na primeira tentativa, uma implementação com um bug sutil (erro de off-by-one num laço), para exercitar o mecanismo de correção — o Dafny real reportou dois diagnósticos genuínos (pós-condição não provada e risco de violar o limite do `newtype`), e uma segunda instância, sem ter visto o código da tentativa anterior, corrigiu usando apenas esse diagnóstico.

**Por que isso não é o experimento da Seção 9, apesar de ter sido executado de verdade**: foi N=1 por grupo, sem repetição; usou só 1 das 5 tarefas da Seção 7.2; o bug da tentativa 1 do grupo C foi pedido deliberadamente, não espontâneo; e os critérios de sucesso foram aplicados de forma ad-hoc, não pré-registrados antes da execução como a Seção 9.3 exige. Por isso esses registros ficaram fora de `results/runs.jsonl` (ver `results/README.md`) — o piloto demonstra que o encanamento funciona ponta a ponta com um agente real, não substitui a execução da metodologia de três braços em escala.

O que **ainda não** foi feito: nenhuma chamada real ao caminho `AnthropicBackend`/API do orquestrador (o piloto acima usou uma via diferente — ver `docs/orchestration.md` §10); as tarefas 2–5 da Seção 7.2 ainda não têm o arnês de teste portado; não há script de varredura (tarefa × grupo × repetições); e, portanto, nenhuma execução da metodologia da Seção 9 em escala. Isso continua sendo hipótese de trabalho futuro, não resultado — ver `docs/orchestration.md` §§8–9 para a lista honesta de limitações e próximos passos.

## 11. Resultados

`[RESULTADO FUTURO — nenhum resultado da metodologia de três braços da Seção 9, em escala, foi produzido nesta versão. Um piloto de validação do orquestrador com agente real foi executado e está descrito na Seção 10 (não nesta seção): N=1 por grupo, uma única tarefa, não uma amostra. Esta seção será preenchida com dados reais, incluindo execuções com falha, depois que a metodologia da Seção 9 for de fato executada em escala — repetições, as cinco tarefas, critérios pré-registrados.]`

## 12. Discussão

`[A preencher após resultados reais existirem. Discussão prematura sem dados seria especulação disfarçada de análise.]`

## 13. Limitações e ameaças à validade

- **Especificação incorreta, incompleta ou excessivamente restritiva**: o contrato revisado é o gabarito do experimento; um gabarito errado invalida a avaliação inteira, não apenas uma tarefa.
- **Provas condicionadas a hipóteses**: toda garantia é relativa às hipóteses declaradas (pré-condições, contratos de dependências assumidos). Hipóteses erradas produzem garantias vazias.
- **Diferença entre matemática idealizada e semântica da linguagem**: o exemplo da Seção 4 mostra isso diretamente — a prova sobre `int` matemático não transfere automaticamente para um tipo de largura fixa sem hipótese adicional de não-overflow.
- **Limitações de suporte das ferramentas**: Dafny tem problemas documentados de explosão de axiomas/triggers causando timeout; isso afeta diretamente a frequência esperada de UNKNOWN (Seção 9.4).
- **Confiança no verificador, solucionador e cadeia de execução**: a garantia nunca é mais forte que a base de confiança descrita na Seção 3.10.
- **Contratos de dependências não verificadas**: qualquer chamada a código fora do escopo de verificação introduz uma hipótese não demonstrada.
- **Custo de manutenção dos contratos**: contratos envelhecem com o código; manter essa sincronia tem custo contínuo, medido na Seção 9.4 ("tempo de escrita e revisão de contratos"), não um custo único.
- **Limites de tempo e de automação**: orçamento de tentativas/tempo/tokens é finito por desenho; resultados não distinguem "o agente não conseguiria" de "o agente não teve orçamento suficiente".
- **Generalização de exemplos pequenos para sistemas reais**: as tarefas da Seção 7.2 são funções puras pequenas; nada aqui generaliza automaticamente para um microsserviço completo ou para propriedades distribuídas (Seção 7.2, idempotência).
- **Viés de seleção de tarefas**: a escolha das cinco tarefas não é amostra aleatória do espaço de problemas de verificação; é uma amostra de conveniência pedagógica.
- **Possível exposição prévia do modelo aos exercícios**: tarefas de verificação formal "clássicas" (soma com invariante, busca em sequência) podem estar presentes em dados de treinamento dos modelos avaliados, inflando desempenho de forma não relacionada à metodologia proposta.
- **Mudanças de comportamento entre versões de modelos**: resultados registrados ficam atrelados à versão de modelo usada (Seção 9.3); não se generalizam automaticamente para versões futuras.
- **Diferença entre verificar um modelo e verificar a implementação**: mencionada na Seção 3.9 — relevante em particular para qualquer extensão futura a propriedades de sistemas distribuídos (idempotência, Seção 7.2).

## 14. Conclusão

`[A preencher após execução da metodologia proposta. Nesta versão, o projeto oferece: uma pergunta de pesquisa delimitada, uma revisão honesta de trabalhos relacionados que reduz — sem eliminar — o espaço de contribuição alegável, um desenho experimental de três braços com controles explícitos de integridade, e um protótipo mínimo reprodutível em Dafny. Nenhuma alegação de resultado é feita até que a Seção 11 seja preenchida com dados reais.]`

## Referências

Ver `paper/references.bib`. Entradas marcadas `[VERIFICAR-ANTES-SUBMETER]` usam IDs de arXiv no formato sugestivo de janeiro/2026 e precisam de confirmação manual de resolução em arxiv.org antes de qualquer submissão formal deste paper. Entradas marcadas `[CLÁSSICO-NÃO-REVERIFICADO]` são referências fundacionais amplamente conhecidas mas não re-confirmadas via busca nesta sessão específica — confirmar via DBLP/ACM/editora antes de submeter.
